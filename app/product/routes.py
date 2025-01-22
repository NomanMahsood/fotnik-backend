from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from app.core.auth import get_current_user, User
from app.db import get_supabase_client
import boto3
import os
from fastapi.responses import StreamingResponse
import requests

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('aws_access_key_id'),
    aws_secret_access_key=os.getenv('aws_secret_access_key')
)
BUCKET_NAME = os.getenv('bucket_name')

class ProductCreate(BaseModel):
    name: str
    target_audience: str
    description: str

class ProductResponse(BaseModel):
    id: str
    name: str
    target_audience: str
    description: str
    user_id: str

class SourcePhotoResponse(BaseModel):
    id: str
    url: str
    created_at: str

class GeneratedImageResponse(BaseModel):
    id: str
    url: str
    created_at: str

class GeneratedPhotoDetail(BaseModel):
    id: str
    image_url: str
    source_image_url: str
    background_description: Optional[str]
    positive_prompt: Optional[str]
    negative_prompt: Optional[str]
    user_rating: Optional[int]
    no_bg_image_url: Optional[str]
    created_at: str
    caption: Optional[str]

class PhotoRatingUpdate(BaseModel):
    rating: int

class PhotoCaptionUpdate(BaseModel):
    caption: str

@router.post("/", response_model=ProductResponse)
async def create_product(product_data: ProductCreate, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Create product in the product_descriptions table
        product_data_dict = {
            "name": product_data.name,
            "product_description": product_data.description,
            "target_customers": product_data.target_audience
        }
        
        result = supabase.table("product_descriptions").insert(product_data_dict).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create product")
            
        created_product = result.data[0]
        
        # Create entry in user_products table
        user_product_data = {
            "user_id": user.id,
            "product_id": created_product["id"]
        }
        user_product_result = supabase.table("user_products").insert(user_product_data).execute()
        
        if not user_product_result.data:
            # Rollback product creation if user_product entry fails
            supabase.table("product_descriptions").delete().eq("id", created_product["id"]).execute()
            raise HTTPException(status_code=400, detail="Failed to link product to user")
        
        return ProductResponse(
            id=created_product["id"],
            name=created_product["name"],
            target_audience=created_product["target_customers"],
            description=created_product["product_description"],
            user_id=user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[ProductResponse])
async def get_products(request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # First get the user's product IDs from user_products
        user_products_result = supabase.table("user_products")\
            .select("product_id")\
            .eq("user_id", user.id)\
            .execute()
            
        if not user_products_result.data:
            return []
            
        # Get the product IDs
        product_ids = [up["product_id"] for up in user_products_result.data]
        
        # Then get the product details for those IDs
        products_result = supabase.table("product_descriptions")\
            .select("*")\
            .in_("id", product_ids)\
            .execute()
        
        products = []
        for product in products_result.data:
            products.append(ProductResponse(
                id=product["id"],
                name=product["name"],
                target_audience=product["target_customers"],
                description=product["product_description"],
                user_id=user.id
            ))
        
        return products
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, product_data: ProductCreate, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Update product in the product_descriptions table
        product_data_dict = {
            "name": product_data.name,
            "product_description": product_data.description,
            "target_customers": product_data.target_audience
        }
        
        result = supabase.table("product_descriptions").update(product_data_dict).eq("id", product_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        updated_product = result.data[0]
        return ProductResponse(
            id=updated_product["id"],
            name=updated_product["name"],
            target_audience=updated_product["target_customers"],
            description=updated_product["product_description"],
            user_id=user.id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{product_id}")
async def delete_product(product_id: str, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        result = supabase.table("product_descriptions").delete().eq("id", product_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return {"message": "Product deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{product_id}/source-images", response_model=List[SourcePhotoResponse])
async def get_source_images(product_id: str, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # First verify that the user has access to this product
        user_product_result = supabase.table("user_products")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("product_id", product_id)\
            .execute()
            
        if not user_product_result.data:
            raise HTTPException(status_code=404, detail="Product not found or access denied")
        
        # Get source photos for the product
        photos_result = supabase.table("source_photos")\
            .select("id, edited_photo_url, created_at")\
            .eq("product_id", product_id)\
            .order("created_at", desc=True)\
            .execute()
        
        source_images = []
        for photo in photos_result.data:
            if photo["edited_photo_url"]:  # Only include photos that have been processed
                source_images.append(SourcePhotoResponse(
                    id=photo["id"],
                    url=photo["edited_photo_url"],
                    created_at=photo["created_at"]
                ))
        
        return source_images
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{product_id}/images", response_model=List[GeneratedImageResponse])
async def get_generated_images(product_id: str, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # First verify that the user has access to this product
        user_product_result = supabase.table("user_products")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("product_id", product_id)\
            .execute()
            
        if not user_product_result.data:
            raise HTTPException(status_code=404, detail="Product not found or access denied")
        
        # Get generated images for the product
        images_result = supabase.table("product_photos")\
            .select("id, image_url, created_at")\
            .eq("product_id", product_id)\
            .order("created_at", desc=True)\
            .execute()
        
        generated_images = []
        for image in images_result.data:
            generated_images.append(GeneratedImageResponse(
                id=image["id"],
                url=image["image_url"],
                created_at=image["created_at"]
            ))
        
        return generated_images
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/image-proxy")
async def proxy_s3_image(url: str, request: Request):
    """Proxy S3 image requests to handle CORS"""
    try:
        user = get_current_user(request)
        
        # Verify that the URL is from our S3 bucket
        if not url.startswith(f"https://{BUCKET_NAME}.s3.amazonaws.com/"):
            raise HTTPException(status_code=400, detail="Invalid image URL")
            
        # Extract the key from the URL
        key = url.replace(f"https://{BUCKET_NAME}.s3.amazonaws.com/", "")
        
        # Get the image from S3
        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            content_type = s3_response['ContentType']
            
            def iterfile():
                yield from s3_response['Body']
                
            return StreamingResponse(
                iterfile(),
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=31536000"
                }
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="Image not found")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/photos/{photo_id}", response_model=GeneratedPhotoDetail)
async def get_generated_photo(photo_id: str, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Get the photo details
        photo_result = supabase.table("product_photos")\
            .select("*")\
            .eq("id", photo_id)\
            .single()\
            .execute()
            
        if not photo_result.data:
            raise HTTPException(status_code=404, detail="Photo not found")
            
        # Verify user has access to the product this photo belongs to
        user_product_result = supabase.table("user_products")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("product_id", photo_result.data["product_id"])\
            .execute()
            
        if not user_product_result.data:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return GeneratedPhotoDetail(
            id=photo_result.data["id"],
            image_url=photo_result.data["image_url"],
            source_image_url=photo_result.data["source_image_url"],
            background_description=photo_result.data.get("background_description"),
            positive_prompt=photo_result.data.get("positive_prompt"),
            negative_prompt=photo_result.data.get("negative_prompt"),
            user_rating=photo_result.data.get("user_rating"),
            no_bg_image_url=photo_result.data.get("no_bg_image_url"),
            created_at=photo_result.data["created_at"],
            caption=photo_result.data.get("caption")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/photos/{photo_id}/rating", response_model=GeneratedPhotoDetail)
async def update_photo_rating(photo_id: str, rating_data: PhotoRatingUpdate, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Verify user has access to the photo
        photo_result = supabase.table("product_photos")\
            .select("product_id")\
            .eq("id", photo_id)\
            .single()\
            .execute()
            
        if not photo_result.data:
            raise HTTPException(status_code=404, detail="Photo not found")
            
        # Verify user has access to the product
        user_product_result = supabase.table("user_products")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("product_id", photo_result.data["product_id"])\
            .execute()
            
        if not user_product_result.data:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update the rating
        if not 1 <= rating_data.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
            
        update_result = supabase.table("product_photos")\
            .update({"user_rating": rating_data.rating})\
            .eq("id", photo_id)\
            .execute()
            
        if not update_result.data:
            raise HTTPException(status_code=400, detail="Failed to update rating")
            
        return GeneratedPhotoDetail(**update_result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/photos/{photo_id}/caption", response_model=GeneratedPhotoDetail)
async def update_photo_caption(photo_id: str, caption_data: PhotoCaptionUpdate, request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Verify user has access to the photo
        photo_result = supabase.table("product_photos")\
            .select("product_id")\
            .eq("id", photo_id)\
            .single()\
            .execute()
            
        if not photo_result.data:
            raise HTTPException(status_code=404, detail="Photo not found")
            
        # Verify user has access to the product
        user_product_result = supabase.table("user_products")\
            .select("*")\
            .eq("user_id", user.id)\
            .eq("product_id", photo_result.data["product_id"])\
            .execute()
            
        if not user_product_result.data:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update the caption
        update_result = supabase.table("product_photos")\
            .update({"caption": caption_data.caption})\
            .eq("id", photo_id)\
            .execute()
            
        if not update_result.data:
            raise HTTPException(status_code=400, detail="Failed to update caption")
            
        return GeneratedPhotoDetail(**update_result.data[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 