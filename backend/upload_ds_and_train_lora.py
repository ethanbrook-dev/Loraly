import os, requests
from huggingface_hub import HfApi
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str) -> dict:
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"

    api = HfApi(token=os.getenv('HF_TOKEN'))

    uploaded_ds_to_hf = upload_ds_to_hf(api, dataset_repo_id, dataset_file_path)
    if uploaded_ds_to_hf:
        train_lora_via_runpod(lora_id, dataset_repo_id)
    else:
        return {"status": "error", "message": "Failed to upload dataset to Hugging Face."}

    return {...}

def upload_ds_to_hf(api, dataset_repo_id, dataset_file_path) -> bool:
    try:
        api.create_repo(
            repo_id=dataset_repo_id,
            repo_type="dataset",
            private=True,
            exist_ok=True
        )
        print("✅ Private dataset repo created (or already exists).")
    except Exception as e:
        return {"status": "error", "message": f"Failed to create dataset repo: {e}"}

    try:
        api.upload_file(
            path_or_fileobj=dataset_file_path,
            path_in_repo="data.jsonl",
            repo_id=dataset_repo_id,
            repo_type="dataset"
        )
    except Exception as e:
        print(f"❌ Failed to create dataset repo: {e}")
        return {"status": "error", "message": f"Failed to upload dataset file: {e}"}

def train_lora_via_runpod(lora_id: str, dataset_repo_id: str):
    pod_id = create_runpod_training_pod(lora_id, dataset_repo_id)
    ...

def create_runpod_training_pod(lora_id: str, dataset_repo_id: str) -> str:
    pod_name = f"{lora_id}-trainer"
    image_name = "ghcr.io/axolotl-llm/axolotl:latest"

    PREFERRED_GPUS = [
        "NVIDIA A40", "NVIDIA A30", "NVIDIA RTX A5000",
        "NVIDIA RTX 6000 Ada Generation", "NVIDIA L40", "NVIDIA L40S",
        "NVIDIA RTX A6000", "NVIDIA RTX 5000 Ada Generation",
        "NVIDIA RTX A4500", "NVIDIA RTX 4000 Ada Generation"
    ]

    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }

    for gpu_type_id in PREFERRED_GPUS:
        payload = {
            "cloudType": "ON_DEMAND",
            "gpuCount": 1,
            "gpuTypeId": gpu_type_id,
            "volumeInGB": 50,
            "containerDiskInGB": 30,
            "name": pod_name,
            "imageName": image_name,
            "env": {
                "HF_TOKEN": os.getenv('HF_TOKEN'),
                "HF_USERNAME": os.getenv('HF_USERNAME'),
                "BASE_MODEL": os.getenv('BASE_MODEL'),
                "DATASET_REPO": dataset_repo_id
            },
            "dockerArgs": "--shm-size=1g",
        }

        response = requests.post(
            "https://api.runpod.io/graphql",
            json={
                "query": """
                mutation CreatePod($input: PodInput!) {
                  podCreate(input: $input) {
                    id
                    status
                  }
                }
                """,
                "variables": {"input": payload}
            },
            headers=headers
        )

        data = response.json()

        if "errors" in data:
            print(f"❌ Failed to create pod with {gpu_type_id}: {data['errors']}")
            continue  # Try next GPU
        else:
            pod_id = data["data"]["podCreate"]["id"]
            print(f"✅ Pod created with {gpu_type_id}: {pod_id}")
            return pod_id

    print("❌ All preferred GPU types failed. Could not create pod.")
    return None