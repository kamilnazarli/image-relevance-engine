from scipy.spatial.distance import cosine
import psycopg
from dotenv import load_dotenv
import os
import json
from google import genai
import re

load_dotenv()

SYSTEM_PROMPT = """
    You are a content-image relevance validator. Your job is to validate whether a candidate image
    is appropriate for the blog post.

    Evaluation rules:
    1. Subject & Species match: If the post is about a specific animal (e.g., Arctic wolf),
    a domestic dog must be REJECTED. Never substitute wild animals with domestic pets or different species.
    2. Domain check: If the post is technical or editorial (e.g., database indexing, software
    watchdog), REJECT any literal animal photos. Metaphors do not qualify for literal images.
    3. Setting: Domestic indoor pets wearing clothes must not represent wild nature posts.

    Return a JSON object matching this structure:
    {
      "approved": true/false,
      "reason": ""
    }
"""

def clean_json_response(raw_output):

    text = raw_output.strip()

    # Remove ```json  ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

def llm_guard(post_data, img_data):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    PROMPT = f"""
        POST DETAILS:
        - Target subject: {post_data.get('target_subject')}
        - Title: {post_data.get('title')}
        - Content: {post_data.get('content')}

        IMAGE DETAILS:
        - Detected subject: {img_data.get('subject')}
        - Category: {img_data.get('category')}
        - Caption: {img_data.get('caption')}
        - Attributes: {img_data.get('attributes')}

"""
    try:
        interaction = client.interactions.create(
            model="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT,
            input=PROMPT,
            response_format={
                "type": "text",
                "mime_type": "application/json"
            }
        )
        clean_response = clean_json_response(interaction.output_text)
        return json.loads(clean_response)
    except Exception as e:
        # if LLM check fails
        return {
            "approved": False,
            "reason": f"Guard verification error: {str(e)}"
        }

def get_most_similar_images(target_id):

    with psycopg.connect(host=os.getenv("DB_HOST"),
                        port=os.getenv("DB_PORT"),
                        dbname=os.getenv("DB_NAME"),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD"))as conn:
        with conn.cursor() as cur:

            cur.execute("""SELECT embedding_vector FROM embeddings
                           WHERE entity_id=%s AND
                           entity_type='post'
                           """, (target_id,))
            row = cur.fetchone()
            if not row:
                return [], {}
            post_embedding = row[0]

            cur.execute("""SELECT entity_id, embedding_vector FROM embeddings
                           WHERE entity_type='image'""")
            img_embeddings = cur.fetchall()
            print(img_embeddings)

            similarity_scores = {}
            for img_id, img_embedding in img_embeddings:
                print(post_embedding)

                sim = 1 - cosine(post_embedding, img_embedding)
                similarity_scores.update({img_id: sim})

            sorted_similarity_scores = dict(sorted(similarity_scores.items(), key=lambda item: item [1], reverse=True))

            print(f"Sorted similarity scores: {sorted_similarity_scores}")

            # fetching TOP 3 highest-scores image metadata
            top3_ids  = [img_id for img_id, _ in  list(sorted_similarity_scores.items())[:3]]
            if not top3_ids:
                return [], sorted_similarity_scores
            
            top3_metadata = cur.execute("""SELECT * FROM image_metadata
                                           WHERE image_id = ANY(%s)
                                           ORDER BY array_position(%s, image_id);""",
                                           (top3_ids, top3_ids)).fetchall()
            
            conn.commit()

    return  top3_metadata, sorted_similarity_scores


def mismatch_guard(target_id, top_metadata, sorted_similarity_scores):
    
    status = "rejected"
    post_id = target_id
    img_id = None
    top_candidate_img_id = None
    similarity_score = 0.0
    notes = []

    if not top_metadata:
        notes.append("No candidate images retrieved")
        return post_id, None, None, 0.0, "no_match", notes

    with psycopg.connect(host=os.getenv("DB_HOST"),
                         port=os.getenv("DB_PORT"),
                         dbname=os.getenv("DB_NAME"),
                         user=os.getenv("DB_USER"),
                         password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:

            cur.execute(
              "SELECT title, content, target_subject FROM posts WHERE id = %s",
              (post_id,),
        )
            post_row = cur.fetchone()
            post_data = {
                "title": post_row[0],
                "content": post_row[1],
                "target_subject": post_row[2],
            }
            # top candidate for logging
            top_candidate = top_metadata[0]
            top_candidate_img_id = top_candidate[1]

            similarity_score = sorted_similarity_scores.get(top_candidate_img_id, 0.0)

            # Evaluate candidates in similariy order
            for cand in top_metadata:
                c_image_id = cand[1]
                c_subject = cand[2]
                c_category = cand[3]
                c_attributes = cand[4]
                c_caption = cand[5]
                c_confidence = cand[6]
                c_sim = sorted_similarity_scores.get(c_image_id, 0.0)

                if c_confidence < 0.7:
                    notes.append(
                        f"Image {c_image_id} skipped: low vision confidence"
                        f" ({c_confidence:.2f})"
                    )
                    continue

                if c_sim < 0.40:
                    notes.append(
                        f"Image {c_image_id} skipped: similarity below threshold"
                        f" ({c_sim:.3f})"
                    )
                    continue

                img_data = {
                    "subject": c_subject,
                    "category": c_category,
                    "attributes": c_attributes,
                    "caption": c_caption,
                }

                guard_decision = llm_guard(post_data, img_data)

                if guard_decision.get("approved"):
                    img_id = c_image_id
                    similarity_score = c_sim
                    status = "approved"
                    notes.append(f"Approved: {guard_decision.get('reason')}")
                    break   # Match found
                else:
                    notes.append(
                        f"Image {c_image_id} is rejected by guard:"
                        f"{guard_decision.get('reason')}"
                    )

            # record outcome in match_reviews
            cur.execute(
                """
                    INSERT INTO match_reviews (image_id, post_id, status, similarity_score, notes)
                    VALUES (%s, %s, %s, %s, %s);
                  """,
                (img_id, post_id, status, similarity_score, json.dumps(notes)),)

            conn.commit()

    return post_id, img_id, top_candidate_img_id, similarity_score, status, notes