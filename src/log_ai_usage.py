from google import genai
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

PRICING = {
    "gemini-2.5-flash":{
        "input": {"text": 0.30, "image": 0.30},
        "output": 2.5
    },
    "gemini-3.8-flash":{
        "input": {"text": 1.50, "image": 1.50},
        "output": 3.75
    },
    "gemini-embedding-2": {
        "input": {"text": 0.20, "image": 0.45},
        "output": 0

    }
}

SYSTEM_PROMPT = """
    You are an image analysis engine. Return only the requested structured fields.
    Keep captions concise (under 30 words) and attribute tags to short 1-2 word descriptors.
    Be direct and do not include conversational preamble or markdown code blocks.
"""

def calculate_cost(usage, model_name):

    print(usage)    
    print(type(usage))

    prompt_tokens = usage.total_input_tokens
    completion_tokens = usage.total_tokens

    model_pricing = PRICING[model_name]

    output_price = model_pricing["output"]

    input_cost = 0
    for modality_tokens in usage.input_tokens_by_modality:
        if modality_tokens.modality == "image":
            input_price = model_pricing["input"]["image"]

        elif modality_tokens.modality == "text":
            input_price = model_pricing["input"]["text"]

        input_cost += modality_tokens.tokens * input_price / 1_000_000

    output_cost = completion_tokens * output_price / 1_000_000
    total_cost_usd = input_cost + output_cost

    # print(f"Input tokens: {prompt_tokens}")
    # print(f"Output tokens: {completion_tokens}")
    # print(f"Total cost in usd: {total_cost_usd}")
    # print(f"Called type: {called_type}")

    return prompt_tokens, completion_tokens, total_cost_usd


def log_cost(usage, model_name, called_type):

    prompt_tokens, completion_tokens, total_cost_usd = calculate_cost(usage, model_name)

    try:
        with psycopg.connect(host=os.getenv("DB_HOST"),
                            port=os.getenv("DB_PORT", 5432),
                            dbname=os.getenv("DB_NAME"),
                            user=os.getenv("DB_USER"),
                            password=os.getenv("DB_PASSWORD")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_cost_logs (model_name, called_type, prompt_tokens,
                                            completion_tokens, cost_usd)
                    VALUES(%s, %s, %s, %s, %s)""",
                    (model_name, called_type, prompt_tokens,
                    completion_tokens, total_cost_usd))
                conn.commit()

        print("AI cost logged successfully!")

    except Exception as e:
        print(f"An error occured: {e}")




# client = genai.Client(
#     api_key=os.getenv("GEMINI_API_KEY")
# )

# interaction = client.interactions.create(
#     model="gemini-2.5-flash",
#     input="Hello. What is up?"
# )

# print(interaction.output_text)

# log_cost(interaction.usage, "gemini-2.5-flash")

# client = genai.Client(
#             api_key=os.getenv("GEMINI_API_KEY"),)

# my_file = client.files.upload(file=r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\data\images\image-1.png")

# interaction = client.interactions.create(
#             model="gemini-3.8-flash",
#             input=[
#                 {
#                     "type": "text", "text": SYSTEM_PROMPT
#                 },
#                 {
#                     "type": "image",
#                     "uri": my_file.uri,
#                     "mime_type": my_file.mime_type,
#                 }
#             ],
#             response_format={
#                     "type": "text",
#                     "mime_type": "application/json",
#                     # "schema": ImageAnaylsisResult.model_json_schema()
#             }
#         )

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="Hello world"
)

# log_cost(result.usageMetadata)

print(type(result))
print(result)