from google import genai
import os
from dotenv import load_dotenv
import psycopg

from .log_ai_usage import log_cost

load_dotenv()

def process_embedding(id, entity_type, embedding_vector):
    """
        Inserting an individual embedding to the table
    """

    with psycopg.connect(host=os.getenv("DB_HOST"),
                         port=os.getenv("DB_PORT", 5432),
                         dbname=os.getenv("DB_NAME"),
                         user=os.getenv("DB_USER"),
                         password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO embeddings (entity_id, entity_type, embedding_vector)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (entity_id, entity_type) DO UPDATE
                            SET embedding_vector = EXCLUDED.embedding_vector;""",
                        (id, entity_type, embedding_vector))
            conn.commit()


def get_embedding(input):
    """
        Receiving embedding from embedding model
    """

    MODEL_NAME = "gemini-embedding-2"

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    result = client.models.embed_content(
        model=MODEL_NAME,
        contents=input
    )

    return result.embeddings[0].values

if __name__ == "__main__":

    print(get_embedding("Go and get it!"))