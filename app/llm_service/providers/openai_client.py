from dataclasses import dataclass
import base64
from pydantic import BaseModel
from openai import OpenAI
from ..prompt_utils import generate_inpaint_prompt


class PhotoGenerationContext(BaseModel):
    positive_prompt: str
    negative_prompt: str
    
# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    


def generate_ad_photo_prompt(product_image: str, product_description: str, target_audience: str, target_photo_description: str | None = None):
    ad_photo_generation_prompt = generate_inpaint_prompt(product_description, target_audience, target_photo_description)
    client = OpenAI()
    
    # First, get the vision model to analyze the image and context
    vision_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": ad_photo_generation_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": product_image if product_image.startswith('http') else f"data:image/jpeg;base64,{product_image}"
                        }
                    }
                ]
            }
        ]
    )
    
    # Use the vision model's response to generate structured output
    structured_response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Based on the analysis, generate a structured output with positive and negative prompts for the ad-inpaint model."
            },
            {
                "role": "user",
                "content": vision_response.choices[0].message.content
            }
        ],
        response_format=PhotoGenerationContext
    )
    
    return structured_response.choices[0].message.parsed
