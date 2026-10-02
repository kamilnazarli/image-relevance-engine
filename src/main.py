import os
from dotenv import load_dotenv

from fastapi import FastAPI
import psycopg

from .embedding import get_embedding, process_embedding
from .search_engine import get_most_similar_images, mismatch_guard
from .schemas import Post

load_dotenv()

app = FastAPI()

@app.get("/")
async def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ""}

@app.post("/posts")
async def get_post(post: Post):
    with psycopg.connect(host=os.getenv("DB_HOST"),
                        port=os.getenv("DB_PORT", 5432),
                        dbname=os.getenv("DB_NAME"),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO posts (title, content, target_subject)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (title) DO UPDATE
                           SET title = EXCLUDED.title
                           RETURNING id;""",
                           (post.title, post.content, post.target_subject))
            post_id = cur.fetchone()[0]

            # !!! Problem! whenever the post already exists in table it will fail here
            
            print(f"Post id: {post_id}")
            conn.commit()
            input = f"Subject: {post.target_subject}\nTitle: {post.title}\nDescription: {post.content}"
            post_embedding = get_embedding(input)
            process_embedding(post_id, "post", post_embedding)

            top_metadata, sorted_similarity_scores = get_most_similar_images(post_id)
            post_id, img_id, top_candidate_img_id, similarity_score, status, reason = (
                mismatch_guard(post_id, top_metadata, sorted_similarity_scores))

            if img_id is None:
                return reason

            cur.execute("""SELECT (file_path, source_url) FROM images WHERE id = %s""",
                            (img_id,))
            conn.commit()

            recommended_file_path, recommended_img_url = cur.fetchone()[0]


            return f"""Recommended image file path: {recommended_file_path}, 
                       source_url: {recommended_img_url}. 
                       {reason}"""
