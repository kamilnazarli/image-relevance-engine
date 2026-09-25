from src.schemas import ImageAnaylsisResult
import base64
from google import genai

from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv() # get environment variables

def llm_default_response():

    res = ImageAnaylsisResult(subject="default",
                              category="default",
                              attributes=["default"],
                              caption="default",
                              confidence=0.5)
    return res

def analyze_image(image_path):
    with open(image_path,
              "rb") as f:
        image_bytes = f.read()

    if os.getenv("LLM_STUB").lower() in ["true", "1", "yes"]:
        return llm_default_response(), " "

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        interaction = client.interactions.create(
            model="gemini-3.8-flash",
            input=[
                {
                    "type": "text", "text": "Caption this image."
                },
                {
                    "type": "image",
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
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
    except:
        print("Fall to exception block")
        return llm_default_response(), " "


if __name__ == "__main__":
    # To test whether API returns result
    images_folder = Path(r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\data\images")

    for image_path in images_folder.iterdir():
        print(image_path)
        print(analyze_image(image_path))
        break