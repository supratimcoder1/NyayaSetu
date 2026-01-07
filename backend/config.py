import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_for_dev") # Fallback only for safety, but generated one is better
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    CHROMA_DB_DIR = "chroma_db_store"
    DATA_DIR = "data"

settings = Settings()
