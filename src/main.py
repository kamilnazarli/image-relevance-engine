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
            post_id = cur.execute("""INSERT INTO TABLE posts VALUES (%s, %s, %s) RETURNING id;""",
                                (post.title, post.content, post.target_subject))
            conn.commit()

    input = post.title + "\n\n" + post.content
    post_embedding = get_embedding(input)
    process_embedding(post_id, "post", post_embedding)

    top_metadata, sorted_similarity_scores = get_most_similar_images(post_id)
    mismatch_guard(post_id, top_metadata, sorted_similarity_scores)
