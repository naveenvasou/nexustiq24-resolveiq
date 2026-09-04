"""
Configuration management for ResolveIQ.
"""
import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ARTICLES_DIR = DATA_DIR / "articles"
ACCOUNTS_DIR = DATA_DIR / "accounts"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
EMBEDDINGS_CACHE_PATH = DATA_DIR / "precomputed_embeddings.json"
STATIC_DIR = BASE_DIR / "static"

class Settings(BaseModel):
    app_name: str = "ResolveIQ"
    track: int = 4
    isp_brand: str = "NexusTel Broadband & Mobile"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    llm_model: str = "gemini-2.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    port: int = 8000
    host: str = "0.0.0.0"

settings = Settings()
