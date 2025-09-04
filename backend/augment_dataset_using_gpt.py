# backend/augment_dataset_using_gpt.py

import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

# Parse list
OPENAI_API_KEYS = [k.strip() for k in os.getenv("OPENAI_API_KEYS", "").split(",") if k.strip()]

# Create an iterator
api_key_iter = iter(OPENAI_API_KEYS)

def get_next_api_key() -> str | None:
    """Return the next API key, or None if we're out."""
    try:
        return next(api_key_iter)
    except StopIteration:
        return None

def augment_dataset_with_gpt(dataset_jsonl_str: str, target_words: int) -> str:
    pass