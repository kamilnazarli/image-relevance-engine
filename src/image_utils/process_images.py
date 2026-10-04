import psycopg
from dotenv import load_dotenv
import os
from .vision import analyze_image
import json

load_dotenv()

def analyze_images():
    with psycopg.connect(host=os.getenv("DB_HOST"),
                        port=os.getenv("DB_PORT", 5432),
                        dbname=os.getenv("DB_NAME"),
                        user=os.getenv("DB_USER"),
                        password=os.getenv("DB_PASSWORD")) as conn:
        
        with conn.cursor() as cur:
            conn.commit()
            res = cur.execute("""SELECT * FROM images
                                WHERE id NOT IN (SELECT image_id FROM image_metadata);
                                """)
            print("Got images")
            for image in res.fetchall():
                print(image)
                image_analysis, usage = analyze_image(image[1])

                print(image_analysis)
                print(type(image_analysis))

                subject, category = image_analysis.subject, image_analysis.category
                attributes, caption = image_analysis.attributes, image_analysis.caption
                image_id, confidence = image[0], image_analysis.confidence

                if confidence < 0.7:
                    status = "flagged_low_confidence"
                    cur.execute("""
                        INSERT INTO image_metadata (image_id, subject, category, attributes,
                                                    caption, confidence, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                        (image_id, subject, category, json.dumps(attributes), caption, confidence, status))
                    conn.commit()

                else:
                    # the default is already 'approved' in table

                    cur.execute("""
                        INSERT INTO image_metadata (image_id, subject, category, attributes,
                                                    caption, confidence)
                        VALUES (%s, %s, %s, %s, %s, %s);""",
                        (image_id, subject, category, json.dumps(attributes), caption, confidence))
                    conn.commit()


if __name__ == "__main__":
    analyze_images()