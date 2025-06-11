import os
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def getHFToken() -> str:
    return os.getenv("HF_TOKEN")

def getHFUsername() -> str:
    return os.getenv("HF_USERNAME")