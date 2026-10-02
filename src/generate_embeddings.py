import psycopg
from dotenv import load_dotenv
import os
from .embedding import get_embedding

load_dotenv()

def process_embeddings():
    """
    Generating embeddings for existing images and posts 
    """
    with psycopg.connect(host=os.getenv("DB_HOST"),
                         port=os.getenv("DB_PORT", 5432),
                         dbname=os.getenv("DB_NAME"),
                         user=os.getenv("DB_USER"),
                         password=os.getenv("DB_PASSWORD")) as conn:
        with conn.cursor() as cur:
        
            # Embed image captions
            res = cur.execute("""SELECT * FROM image_metadata
                              WHERE caption != 'default'
                                    AND image_id NOT IN
                                    (SELECT entity_id FROM embeddings
                                        WHERE entity_type='image')""")
            
            for image in res.fetchall():
            
                image_id = image[1]
                caption = image[5]
                attributes = image[4] # Optionally to convert attributes to embedding
    
                input = caption + "\n\n" + str(attributes) # input turn to embedding
                image_embedding = get_embedding(input)
    
                # Put the embedding into the table
                cur.execute("""INSERT INTO embeddings (entity_id, entity_type, embedding_vector)
                            VALUES (%s, %s, %s)""",
                            (image_id, "image", image_embedding))
                conn.commit()
    
            # Embed blog posts
            res = cur.execute("""SELECT * FROM posts WHERE id NOT IN
                                (SELECT entity_id FROM embeddings WHERE entity_type='post')""")
            for post in res.fetchall():
            
                post_id = post[0]
    
                input = post[1] + "\n\n" + post[2]
                input = f"Subject: {post[3]}\nTitle: {post[1]}\nDescription: {post[2]}"

                post_embedding = get_embedding(input)

                cur.execute("""INSERT INTO embeddings (entity_id, entity_type, embedding_vector)
                            VALUES (%s, %s, %s)""",
                            (post_id, "post", post_embedding))

                conn.commit()


if __name__ == "__main__":
    process_embeddings()