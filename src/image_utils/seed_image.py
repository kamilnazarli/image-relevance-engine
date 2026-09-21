import psycopg
from pathlib import Path
import json
import os
from dotenv import load_dotenv

load_dotenv()

image = {}

with open(r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\image_links.json", "r") as f:
    # to get source links of images
    links = json.load(f)[0]
    # print(type(links))

# Folder path that holds images in it
folder = Path(r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\data\images")
for file_path in folder.iterdir():
    # print(file_path)
    image["file_path"] = str(file_path)
    image["source_url"] = links[file_path.name]

    with psycopg.connect(host=os.getenv("DB_HOST"),
                         port=os.getenv("DB_PORT", 5432),
                         dbname=os.getenv("DB_NAME"),
                         user=os.getenv("DB_USER"),
                         password=os.getenv("DB_PASSWORD"),) as conn:

        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO images (file_path, source_url) VALUES (%s, %s)
                ON CONFLICT (file_path) DO NOTHING;
                """,
                (image["file_path"], image["source_url"])
        )
        conn.commit()