import psycopg
import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

def log_posts():

    BASE_DIR = Path(__file__).resolve().parent.parent.parent  # root directory
    POSTS_FILE = BASE_DIR / "data" / "sample_posts.json"

    with open(POSTS_FILE, mode="r") as file:
        sample_posts = json.load(file)

    with psycopg.connect(host=os.getenv("DB_HOST"),
                         port=os.getenv("DB_PORT", 5432),
                         dbname=os.getenv("DB_NAME"),
                         user=os.getenv("DB_USER"),
                         password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:
            cur.executemany("""INSERT INTO posts (title, content, target_subject)
                        VALUES (%s, %s, %s)""",
                        [(post["title"], post["content"], post["target_subject"])
                         for post in sample_posts]
                        )
            conn.commit()


if __name__ == "__main__":
    log_posts()
    print("All posts logged successfully")