from google import genai
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

def process_embedding(id, entity_type, embedding_vector):
    with psycopg.connect(host=os.getenv("DB_HOST"),
                            port=os.getenv("DB_PORT", 5432),
                            dbname=os.getenv("DB_NAME"),
                            user=os.getenv("DB_USER"),
                            password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO TABLE embeddings VALUES (%s, %s, %s)""",
                        (id, entity_type, embedding_vector))
            conn.commit()


def get_embedding(input):

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    result = client.models.embed_content(
        model="gemini-embedding-2",
        contents=input
    )

    return result.embeddings[0].values

if __name__ == "__main__":

    print(get_embedding("Go and get it!"))