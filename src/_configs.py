import os
from dotenv import load_dotenv

from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    HF_TOKEN: str = os.getenv("HF_TOKEN")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_API_URL: str = os.getenv("GEMINI_API_URL")
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME")

    def __init__(self):
        self._init_openai(url=self.GEMINI_API_URL)
        self._init_hf()

    def _init_openai(self, url: str):
        from openai import OpenAI

        self.client = OpenAI(base_url=url, api_key=self.GEMINI_API_KEY)

    def _init_hf(self):
        from huggingface_hub import HfApi

        self.hf = HfApi(token=self.HF_TOKEN)


settings = Settings()
