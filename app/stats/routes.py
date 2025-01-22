from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from app.core.auth import get_current_user
from app.db import get_supabase_client
import uuid
router = APIRouter(
    prefix="/stats",
    tags=["stats"]
)

@router.get("/user")
async def get_user_stats(current_user: Dict = Depends(get_current_user)):
    """
    Get user statistics including:
    - Number of products
    - Number of generated images
    - Last activity
    - Available tokens
    """
    try:
        activities = []
        supabase = get_supabase_client()
        user_id = current_user.id

        # Get number of products and their IDs
        products_response = supabase.table("user_products")\
            .select("product_id, created_at, updated_at, product_descriptions(name)")\
            .eq("user_id", str(user_id))\
            .execute()
        for product in products_response.data:
            if product["created_at"] == product["updated_at"]:
                activity = {'type': 'product_created', 'product_id': product["product_id"], 'date': product["created_at"], 'name': product["product_descriptions"]["name"]}
            else:
                activity = {'type': 'product_updated', 'product_id': product["product_id"], 'date': product["updated_at"], 'name': product["product_descriptions"]["name"]}
            activities.append(activity)
        product_ids = [product["product_id"] for product in products_response.data]  # Already strings from JSON
        num_products = len(products_response.data)
        
        # Simple query to get source photos
        source_photos_response = supabase.table("source_photos")\
            .select("id, original_photo_url, edited_photo_url, product_id, created_at")\
            .in_("product_id", product_ids)\
            .execute()
            
        for source_photo in source_photos_response.data:
            activity = {'type': 'source_photo_uploaded', 'product_id': source_photo["product_id"], 'date': source_photo["created_at"], 'original_photo_url': source_photo["original_photo_url"], 'edited_photo_url': source_photo["edited_photo_url"]}
            activities.append(activity)
        
        

        # Get number of generated images for user's products
        num_generated_images = 0
        if product_ids:  # Only query if user has products
            images_response = supabase.table("product_photos")\
                .select("id, product_id, image_url, created_at")\
                .in_("product_id", product_ids)\
                .execute()
            for image in images_response.data:
                activity = {
                    'type': 'image_generated', 
                    'product_id': image["product_id"], 
                    'date': image["created_at"], 
                    'image_url': image["image_url"],
                    'photo_id': image["id"]
                }
                activities.append(activity)
            num_generated_images = len(images_response.data)

        # Get last activity (most recent between product creation and image generation)
        activities.sort(key=lambda x: x['date'], reverse=True)
        last_activity = activities[0]['date'] if activities else None
        
    
        
        last_activity = None
        if activities:
            last_activity = activities[0]['date']

        # Get available tokens
        tokens_response = supabase.table("user_tokens")\
            .select("token_balance")\
            .eq("user_id", str(user_id))\
            .single()\
            .execute()
        available_tokens = 0
        if tokens_response.data:
            available_tokens = tokens_response.data["token_balance"]

        return {
            "num_products": num_products,
            "num_generated_images": num_generated_images,
            "last_activity": last_activity,
            "available_tokens": available_tokens,
            "activities": activities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
