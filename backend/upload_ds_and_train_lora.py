import os
from huggingface_hub import HfApi
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str) -> dict:
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"

    api = HfApi(token=os.getenv('HF_TOKEN'))

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

    return {
        # "status": "success",
        # "dataset_repo_id": dataset_repo_id,
        # "dataset_url": f"https://huggingface.co/datasets/{dataset_repo_id}",
        # "model_id": os.getenv('HF_MODEL_ID'),
        # "message": "Dataset created and uploaded successfully. Proceed to fine-tune via RunPod."
        # Smth else ...
    }
