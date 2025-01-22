from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from app.core.auth import get_current_user, get_supabase_client, User, TokenOperationType

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Pydantic models for request/response
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/signin")

@router.post("/signup", response_model=UserResponse)
async def signup(user_data: UserCreate, request: Request):
    """
    Called after successful Supabase authentication to create user profile
    """
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Create user profile in the profiles table
        profile_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user_data.full_name
        }
        
        # Check if the token allocation already exists for the user
        existing_profile = supabase.table("user_tokens").select("*").eq("user_id", user.id).execute()
        if existing_profile.data:
            return UserResponse(**existing_profile.data[0])
            
        # Initialize token allocation for the new user
        token_data = {
            "user_id": user.id,
            "token_balance": 3
        }
        supabase.table("user_tokens").insert(token_data).execute()
        
        return UserResponse(**profile_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/signin")
async def signin(request: Request):
    """
    Called after successful Supabase authentication to validate session
    """
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Get user profile
        token_result = supabase.table("user_tokens").select("*").eq("user_id", user.id).execute()
        
        if not token_result.data:
            raise HTTPException(status_code=404, detail="No token allocation found for user")
            
        return {"message": "Successfully signed in", "user": token_result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/pre-signout")
async def pre_signout(request: Request):
    """
    Called before Supabase sign out to handle any cleanup
    """
    try:
        user = get_current_user(request)
        # Add any cleanup logic here if needed
        return {"message": "Ready for sign out"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_user_profile(request: Request):
    try:
        user = get_current_user(request)
        supabase = get_supabase_client()
        
        # Get user profile from profiles table
        result = supabase.table("user_tokens").select("*").eq("user_id", user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User profile not found")
            
        profile_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.user_metadata.get("full_name")
        }
        return UserResponse(**profile_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 