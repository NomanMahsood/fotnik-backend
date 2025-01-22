from supabase import create_client, Client
from fastapi import Depends, HTTPException, Request
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Type definitions
TokenOperationType = Literal["token_balance"]

__all__ = ['TokenOperationType', 'User', 'UserIdentity', 'get_current_user', 'get_supabase_client']

class UserIdentity(BaseModel):
    id: str
    identity_id: str
    user_id: str
    identity_data: Dict[str, Any]
    provider: str
    created_at: datetime
    last_sign_in_at: datetime
    updated_at: datetime

class User(BaseModel):
    id: str
    app_metadata: Dict[str, Any]
    user_metadata: Dict[str, Any]
    aud: str
    confirmation_sent_at: Optional[datetime]
    recovery_sent_at: Optional[datetime]
    email_change_sent_at: Optional[datetime]
    new_email: Optional[str]
    new_phone: Optional[str]
    invited_at: Optional[datetime]
    action_link: Optional[str]
    email: str
    phone: str
    created_at: datetime
    confirmed_at: Optional[datetime]
    email_confirmed_at: Optional[datetime]
    phone_confirmed_at: Optional[datetime]
    last_sign_in_at: Optional[datetime]
    role: str
    updated_at: datetime
    identities: List[UserIdentity]
    is_anonymous: bool
    factors: Optional[Any]

def get_supabase_client() -> Client:
    """Create and return a Supabase client instance"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
    return create_client(url, key)

def get_current_user(request: Request) -> User:
    """Get the current user from the request's auth header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="No authorization header")
        
    try:
        supabase = get_supabase_client()
        user_result = supabase.auth.get_user(auth_header.split(" ")[1])
        if not user_result.user:
            raise HTTPException(status_code=401, detail="Invalid user token")
        return User(**user_result.user.model_dump())
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid user token: {str(e)}")

def get_current_workspace(request: Request) -> Optional[str]:
    """Get the current workspace ID from the request headers"""
    return request.headers.get("X-Workspace-ID")

async def check_tokens(
    user_id: str, 
    operation_type: TokenOperationType
) -> None:
    """
    Check if user has enough tokens for the operation.
    Raises HTTPException if not enough tokens.
    """
    supabase = get_supabase_client()
    
    result = supabase.table("user_tokens").select("*").eq("user_id", user_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=402, 
            detail={
                "message": "No token allocation found. Please subscribe to a plan.",
                "code": "NO_TOKENS"
            }
        )
        
    tokens = result.data[0]
    current_tokens = tokens[operation_type]
    
    if current_tokens <= 0:
        raise HTTPException(
            status_code=402,
            detail={
                "message": f"Not enough {operation_type.replace('_', ' ')} remaining. Please upgrade your plan.",
                "code": "INSUFFICIENT_TOKENS"
            }
        )

async def reduce_tokens(
    user_id: str, 
    operation_type: TokenOperationType,
    amount: int = 1
) -> None:
    """
    Reduce the user's token count for the specified operation.
    Should only be called after successful completion of the operation.
    """
    supabase = get_supabase_client()
    
    result = supabase.table("user_tokens").select("*").eq("user_id", user_id).execute()
    if not result.data:
        logger.error(f"No token record found for user {user_id} when trying to reduce tokens")
        return
        
    tokens = result.data[0]
    current_tokens = tokens[operation_type]
    
    update_data = {operation_type: max(0, current_tokens - amount)}
    supabase.table("user_tokens").update(update_data).eq("user_id", user_id).execute() 