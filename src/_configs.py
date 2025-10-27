import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    HF_TOKEN: str = os.getenv("HF_TOKEN")
    HF_REPO_ID: str = os.getenv("HF_REPO_ID")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_API_URL: str = os.getenv("GEMINI_API_URL")
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME")
    ROOT_DIR: str = Path(__file__).parent.parent.resolve()  # ./data_enrichment
    MAX_WORKERS: int = os.getenv("MAX_WORKERS", 16)


settings = Settings()
