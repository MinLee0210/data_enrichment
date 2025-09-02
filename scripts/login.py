import os
from dotenv import load_dotenv
from huggingface_hub import login


def init_login():
    load_dotenv()
    login(os.getenv("HUGGINGFACE_TOKEN"))
    print("Login successful")