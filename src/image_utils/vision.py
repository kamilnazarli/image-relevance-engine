from src.schemas import ImageAnaylsisResult
import base64

from google import genai
from google.genai import types

from groq import Groq

from dotenv import load_dotenv
import os
from pathlib import Path



load_dotenv() # get environment variables

SYSTEM_PROMPT = """
    You are an image analysis engine. Return only the requested structured fields.
    Keep captions concise (under 30 words) and attribute tags to short 1-2 word descriptors.
    Be direct and do not include conversational preamble or markdown code blocks.
"""

def llm_default_response():

    res = ImageAnaylsisResult(subject="default",
                              category="default",
                              attributes=["default"],
                              caption="default",
                              confidence=0.5)
    return res


def encode_image(image_path):
    with open(image_path,
                  "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(image_path):

    # Encode the image
    base64_image = encode_image(image_path)

    if os.getenv("LLM_STUB").lower() in ["true", "1", "yes"]:
        return llm_default_response(), " "

    try:
        client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=types.HttpOptions(
                timeout=45_000  # 45 seconds in milliseconds
            ))

        interaction = client.interactions.create(
            model="gemini-3.8-flash",
            input=[
                {
                    "type": "text", "text": SYSTEM_PROMPT
                },
                {
                    "type": "image",
                    "data": base64_image,
                    "mime_type": "image/png",
                }
            ],
            response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ImageAnaylsisResult.model_json_schema()
            }
        )
        return (ImageAnaylsisResult.model_validate_json(interaction.output_text),
                interaction.usage)

    except Exception as e:
        print("Fall to exception block, change to GROQ")

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "image_analysis_result",
                    "schema": ImageAnaylsisResult.model_json_schema()
                }
            },
            max_tokens=500

        )
        return (ImageAnaylsisResult.model_validate_json(completion.choices[0].message.content),
                        completion.usage)
    except:
        return llm_default_response(), " "



if __name__ == "__main__":
    # To test whether API returns result
    images_folder = Path(r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\data\images")

    for image_path in images_folder.iterdir():
        print(image_path)
        print(analyze_image(image_path))
        break