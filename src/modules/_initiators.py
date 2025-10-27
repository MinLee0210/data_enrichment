from huggingface_hub import login
from openai import OpenAI

from src._configs import settings
from src.utils.logger_util import setup_logger

logger = setup_logger()


class Initiator:
    def __init__(self):
        self._init_hf()
        self._init_openai()

    def _init_hf(self):
        try:
            login(settings.HF_TOKEN)
        except Exception as e:
            logger.error(f"Failed to login to Hugging Face: {e}")
            raise e

    def _init_openai(self):
        try:
            self.client = OpenAI(
                base_url=settings.GEMINI_API_URL, api_key=settings.GEMINI_API_KEY
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise e
