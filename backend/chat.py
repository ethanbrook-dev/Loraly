import os
from dotenv import load_dotenv

# Load .env.local
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def chat_with_lora(loraid: str, prompt: str) -> str:
    print("Hey this is the chat_with_lora function. I will return a temp fake response just for show ...")
    response = input("What should the response be?")
    return response