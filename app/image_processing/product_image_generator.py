import asyncio
import replicate
from typing import List
import aiohttp
import os
import base64
import uuid
from datetime import datetime
import boto3
from app.core.auth import get_supabase_client
import logging
from app.llm_service.providers.openai_client import generate_ad_photo_prompt
from app.websockets.connection_manager import manager

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret_access_key')
)
BUCKET_NAME = os.getenv('bucket_name')

async def generate_ad_photo(image: str, product_id: str, access_token: str, refresh_token: str, background_description: str = None):
    """Process image with the given background description.
    
    Args:
        image: Base64 encoded image or image URL
        product_id: ID of the product
        access_token: Bearer access token for authentication
        refresh_token: Bearer refresh token for authentication
        background_description: Optional description of the desired background
    
    Returns:
        dict: Response containing the processed image details and URLs
    """
    try:
        # Send initial status
        await manager.broadcast({
            "type": "processing_status",
            "status": "started",
            "message": "Starting image generation",
            "product_id": product_id
        })

        # Get authenticated user from token
        supabase = get_supabase_client()
        supabase.auth.set_session(access_token, refresh_token)
        user = supabase.auth.get_user()
        user_id = user.user.id
        
        # retrieve the product description and target audience from the product_descriptions table
        await manager.broadcast({
            "type": "processing_status",
            "status": "fetching_product",
            "message": "Fetching product details",
            "product_id": product_id
        })
        
        product_result = supabase.table("product_descriptions").select("product_description, target_customers").eq("id", product_id).execute()
        product_description = product_result.data[0]["product_description"]
        target_audience = product_result.data[0]["target_customers"]
        
        # store the image to the local filesystem
        # generate a unique filename
        filename = f"{uuid.uuid4()}.jpg"
        image_path = f"data/images/source/{filename}"
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image))
            
        await manager.broadcast({
            "type": "processing_status",
            "status": "removing_background",
            "message": "Removing background...",
            "product_id": product_id
        })
        
        img_path_removed_bg_url = await remove_bg(image_path, is_url=False)
 
        removed_bg_path = f"data/images/removed_bg/{filename}"
        
        # save the image from the url to the local filesystem
        async with aiohttp.ClientSession() as session:
            async with session.get(img_path_removed_bg_url) as response:
                content = await response.read()
                with open(removed_bg_path, "wb") as f:
                    f.write(content)
                    
        # Upload source image with removed background to S3
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        source_s3_key = f"products/{product_id}/source_{timestamp}.jpg"
        s3_client.upload_file(removed_bg_path, BUCKET_NAME, source_s3_key)
        source_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{source_s3_key}"
        
        # Upload the image with removed background to S3
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        no_bg_s3_key = f"products/{product_id}/no_bg_{timestamp}.jpg"
        s3_client.upload_file(removed_bg_path, BUCKET_NAME, no_bg_s3_key)
        no_bg_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{no_bg_s3_key}"
        
        await manager.broadcast({
            "type": "processing_status",
            "status": "generating_prompt",
            "message": "Generating AI prompt",
            "product_id": product_id
        })
        
        prompt = generate_ad_photo_prompt(img_path_removed_bg_url, product_description, target_audience, background_description)
        
        await manager.broadcast({
            "type": "processing_status",
            "status": "prompt_generated",
            "message": "Prompt generated successfully, generating images...",
            "product_id": product_id
        })
        
        generated_paths = await generate_ad_photos(prompt.positive_prompt, 4, img_path_removed_bg_url, "0.5 * width", prompt.negative_prompt, "data/images/generated")
        generated_images = [item.url for item in generated_paths][1:]
        
        # Upload images to S3 and get their URLs
        s3_urls = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for idx, image_url in enumerate(generated_images):
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    content = await response.read()
                    local_path = f"data/images/generated/{image_url.split('/')[-1]}"
                    with open(local_path, "wb") as f:
                        f.write(content)
                    
                    # Upload to S3
                    s3_key = f"products/{product_id}/generated_{timestamp}_{idx}.jpg"
                    s3_client.upload_file(local_path, BUCKET_NAME, s3_key)
                    s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                    s3_urls.append(s3_url)
                    
                    # Store image information in product_photos table
                    supabase.table("product_photos").insert({
                        "product_id": product_id,
                        "image_url": s3_url,
                        "source_image_url": source_s3_url,
                        "no_bg_image_url": no_bg_s3_url,
                        "background_description": background_description,
                        "positive_prompt": prompt.positive_prompt,
                        "negative_prompt": prompt.negative_prompt
                    }).execute()
        
        # Store image URLs in response
        response = {
            "status": "success",
            "message": "Images generated and uploaded successfully",
            "source_image_url": source_s3_url,
            "image_urls": s3_urls,
            "product_id": product_id
        }
        
        # Clean up local files if in production
        if os.getenv('ENVIRONMENT') == 'production':
            for file in os.listdir('data/images/generated'):
                os.remove(os.path.join('data/images/generated', file))
            os.remove(image_path)
            os.remove(removed_bg_path)

        await manager.broadcast({
            "type": "processing_status", 
            "message": "Process completed successfully",
            "data": response,
            "product_id": product_id
        })
        
        return response
        
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "product_id": product_id
        }
        
        await manager.broadcast({
            "type": "processing_status",
            "status": "error",
            "message": f"Error processing image: {str(e)}",
            "product_id": product_id
        })
        
        logger.error(f"General error in generate_ad_photo: {str(e)}")
        return error_response

async def generate_ad_photos(
    prompt: str,
    image_num: int,
    image_path: str,
    product_size: str,
    negative_prompt: str,
    output_dir: str = "data/images/generated"
) -> List[str]:
    """
    Generate ad photos using Replicate's ad-inpaint model.
    
    Args:
        prompt: The prompt describing the desired output
        image_num: Number of images to generate
        image_path: URL or path to the input image
        product_size: Size specification for the product
        negative_prompt: Prompt specifying what to avoid in generation
        output_dir: Directory to save generated images
    
    Returns:
        List of paths to the generated images
    """
    input_params = {
        "prompt": prompt,
        "image_num": image_num,
        "image_path": image_path,
        "product_size": product_size,
        "negative_prompt": negative_prompt
    }
    
    # Run the model
    output = replicate.run(
        "logerzhu/ad-inpaint:b1c17d148455c1fda435ababe9ab1e03bc0d917cc3cf4251916f22c45c83c7df",
        input=input_params
    )
    
    return output

async def remove_bg(
    image_input: str,
    is_url: bool = True
) -> str:
    """
    Remove background from an image using Replicate's remove-bg model.
    
    Args:
        image_input: URL or local path to the input image
        output_path: Path where the output image will be saved
        is_url: Boolean indicating if the image_input is a URL (True) or local path (False)
    
    Returns:
        Path to the processed image with background removed
    """
        
    if is_url:
        input_params = {"image": image_input}
    else:
        # Read local file and encode to base64
        with open(image_input, "rb") as f:
            image_data = f.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            input_params = {"image": f"data:image/jpeg;base64,{base64_image}"}
    
    
    # Run the model
    output = replicate.run(
        "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1",
        input=input_params
    )
    
    return output.url

async def add_source_photo(image: str, access_token: str, refresh_token: str, product_id: str) -> dict:
    """Add a source photo with background removed version to S3 and database.
    
    Args:
        image: Base64 encoded image
        access_token: Bearer access token for authentication
        refresh_token: Bearer refresh token for authentication
        product_id: ID of the product
    
    Returns:
        dict: Response containing the original and edited photo URLs
    """
    try:
        # Generate unique filename
        filename = f"{uuid.uuid4()}.jpg"
        image_path = f"data/images/source/{filename}"
        
        # Save original image locally
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image))
            
        # Upload original image to S3
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_s3_key = f"products/{product_id}/original_{timestamp}.jpg"
        s3_client.upload_file(image_path, BUCKET_NAME, original_s3_key)
        original_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{original_s3_key}"
        
        # Remove background
        img_path_removed_bg_url = await remove_bg(image_path, is_url=False)
        
        # Save removed background image locally
        removed_bg_path = f"data/images/removed_bg/{filename}"
        async with aiohttp.ClientSession() as session:
            async with session.get(img_path_removed_bg_url) as response:
                content = await response.read()
                with open(removed_bg_path, "wb") as f:
                    f.write(content)
        
        # Upload removed background image to S3
        edited_s3_key = f"products/{product_id}/edited_{timestamp}.jpg"
        s3_client.upload_file(removed_bg_path, BUCKET_NAME, edited_s3_key)
        edited_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{edited_s3_key}"
        
        # Get authenticated user from token
        supabase = get_supabase_client()
        supabase.auth.set_session(access_token, refresh_token)
        user = supabase.auth.get_user()
        user_id = user.user.id
        
        # Then insert the source photo
        result = supabase.table("source_photos").insert({
            "product_id": product_id,
            "original_photo_url": original_s3_url,
            "edited_photo_url": edited_s3_url
        }).execute()
        
        # Clean up local files if in production
        if os.getenv('ENVIRONMENT') == 'production':
            os.remove(image_path)
            os.remove(removed_bg_path)
            
        return {
            "status": "success",
            "original_photo_url": original_s3_url,
            "edited_photo_url": edited_s3_url,
            "photo_id": result.data[0]['id'] if result.data else None
        }
        
    except Exception as e:
        logger.error(f"Error in add_source_photo: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
        
# TODO: remove metadata that might indicated that the image was generated by AI
# TODO: add a watermark to the image if the user has not purchased the monthly plan?
# TODO: add a feature to generate the instagram caption for the image
