from scipy.spatial.distance import cosine
import psycopg
from dotenv import load_dotenv
import os
import json

load_dotenv()

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
            post_embedding = cur.fetchone()[0]

            cur.execute("""SELECT entity_id, embedding_vector FROM embeddings
                           WHERE entity_type='image'""")
            img_embeddings = cur.fetchall()
            print(img_embeddings)

            similarity_scores = {}
            for img_id, img_embedding in img_embeddings:
                print(post_embedding)
                similarity_scores.update({img_id: 1 - cosine(post_embedding, img_embedding)})

            sorted_similarity_scores = dict(sorted(similarity_scores.items(), key=lambda item: item [1], reverse=True))

            print(f"Sorted similarity scores: {sorted_similarity_scores}")

            # fetching TOP 3 highest-scores image metadata
            top3_ids  = [img_id for img_id, _ in  sorted_similarity_scores.items()]
            top3_metadata = cur.execute("""SELECT * FROM image_metadata
                                           WHERE image_id = ANY(%s)
                                           ORDER BY array_position(%s, image_id);""",
                                           (top3_ids, top3_ids)).fetchall()
            
            conn.commit()

    return  top3_metadata, sorted_similarity_scores


def mismatch_guard(target_id, top_metadata, sorted_similarity_scores):
    
    status = "approved"
    post_id = target_id
    notes = []

    with psycopg.connect(host=os.getenv("DB_HOST"),
                         port=os.getenv("DB_PORT"),
                         dbname=os.getenv("DB_NAME"),
                         user=os.getenv("DB_USER"),
                         password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:

            # if the match catalog is empty
            if len(top_metadata) == 0:
                status = "no match found"
                img_id = None
                similarity_score = None
                notes.append("No catalog image qualified")
                cur.execute("""INSERT INTO match_reviews (image_id, post_id, status, similarity_score, notes)
                               VALUES (%s, %s, %s, %s, %s);""",
                            (img_id, post_id, status, similarity_score, json.dumps(notes)))
            else:

                accepted_images = [] # candidate images which passes the threshold

                # rejecting any image whose confidence < 0.70
                for img in top_metadata:
                    if img[6] < 0.7:
                        print(f"Image {img[1]} rejected because of low confidence.")
                        continue
                    if sorted_similarity_scores[img[1]] < 0.65:
                        print(f"Image {img[1]} rejected because of low similarity.")
                        continue
                    accepted_images.append(img)

                approved_img = top_metadata[0] if len(accepted_images) == 0 else accepted_images[0]
                img_id = approved_img[1]
                top_candidate_img_id = img_id  # //
                similarity_score = sorted_similarity_scores[img_id]

                if len(accepted_images) == 0:
                    print(f"Post {target_id} needs to be reviewed manually")
                    status = "rejected"
                    img_id = None
                    notes.append(f"""Top candidate image id: {top_candidate_img_id}.
                                    Rejected because of low similarity or confidence. Manual review needed.
                                """)
                    cur.execute("""INSERT INTO match_reviews (image_id, post_id, status, similarity_score, notes)
                                VALUES (%s, %s, %s, %s, %s);""",
                                (img_id, post_id, status, similarity_score, json.dumps(notes)))
                else:
                    notes.append("Match found and approved")
                    cur.execute("""INSERT INTO match_reviews (image_id, post_id, status, similarity_score, notes)
                                VALUES (%s, %s, %s, %s, %s);""",
                                (img_id, post_id, status, similarity_score, json.dumps(notes)))
                    
                    # !!! DOMAIN CONFLICT CHECK 

            conn.commit()
    
    if img_id is None:
        print("Mismatch check phase finished. No match found")
    else:
        print(f"Mismatch check phase finished. Found image {img_id}")


    return post_id, img_id, top_candidate_img_id, similarity_score, status, notes