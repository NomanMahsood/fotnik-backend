import os
from dotenv import load_dotenv

# the cwd is the same folder as the current file; make sure to run the file from the backend folder
# get the folder of the current file
current_file_path = os.path.abspath(__file__)
current_file_dir = os.path.dirname(current_file_path)
os.chdir(current_file_dir)

# Load environment variables based on environment
env = os.getenv("ENVIRONMENT", "development")
env_file = f"{current_file_dir}/.env.{env}"

if os.path.exists(env_file):
    load_dotenv(env_file)
elif os.path.exists(".env"):
    load_dotenv(".env")

# Configuration class
class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings() 