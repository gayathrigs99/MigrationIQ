"""Application settings, loaded from environment variables or a .env file."""

from functools import lru_cache
from pathlib import Path
import os
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY")
    llm_model: str 

    chroma_persist_directory: Path = Path("./chroma_db")
    knowledge_base_directory: Path = Path("../knowledge_base")
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    retrieval_results_per_construct: int = 2
    retrieval_max_references: int = 8
    max_correction_attempts: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
