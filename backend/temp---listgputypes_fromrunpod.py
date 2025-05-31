# temp---listgputypes_fromrunpod.py

import os
import requests
from dotenv import load_dotenv

# Load .env.local (assuming it’s one level up from this file)
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def list_gpu_types():
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }

    query = {
        "query": """
        query {
            gpuTypes {
                id
                displayName
                memoryInGb
            }
        }
        """
    }

    response = requests.post("https://api.runpod.io/graphql", json=query, headers=headers)
    data = response.json()

    print("✅ Available GPU Types:\n")
    for gpu in data["data"]["gpuTypes"]:
        print(f"ID: {gpu['id']}\nDisplay Name: {gpu['displayName']}\nMemory: {gpu['memoryInGb']} GB\n---")

if __name__ == "__main__":
    list_gpu_types()
