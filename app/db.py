from supabase import create_client, Client
import os

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and key must be set in environment variables")
    
    return create_client(supabase_url, supabase_key)
