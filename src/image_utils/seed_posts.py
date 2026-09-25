import psycopg
import os
from dotenv import load_dotenv
import json

load_dotenv()

with open(r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\data\sample_posts.json",
          mode="r") as file:
    sample_posts = json.load(file)

with psycopg.connect(host=os.getenv("DB_HOST"),
                     port=os.getenv("DB_PORT", 5432),
                     dbname=os.getenv("DB_NAME"),
                     user=os.getenv("DB_USER"),
                     password=os.getenv("DB_PASSWORD")) as conn:
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO posts (title, content, target_subject)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (title) DO NOTHING""",
                    [(post["title"], post["content"], post["target_subject"])
                     for post in sample_posts]
                    )
        conn.commit()