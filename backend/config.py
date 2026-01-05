import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    CHROMA_DB_DIR = "chroma_db_store"
    DATA_DIR = "data"

settings = Settings()
