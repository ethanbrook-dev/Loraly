import os
from huggingface_hub import HfApi, HfFolder

# How to get HF credentials:
#                           os.getenv("HF_TOKEN")
#                           os.getenv("HF_USERNAME")
#                           os.getenv("HF_MODEL_ID")

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str) -> dict:
    dataset_repo_id = f"{os.getenv("HF_USERNAME")}/{lora_id}-dataset"
    print(f"\n📡 Creating dataset repo: {dataset_repo_id} ...")

    api = HfApi(token=os.getenv("HF_TOKEN"))

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
        print("📤 Dataset file uploaded to Hugging Face.")
    except Exception as e:
        return {"status": "error", "message": f"Failed to upload dataset file: {e}"}

    print("\n🚀 Your dataset is ready for fine-tuning!")
    print(f"📂 Dataset repo: https://huggingface.co/datasets/{dataset_repo_id}")

    return {
        "status": "success",
        "dataset_repo_id": dataset_repo_id,
        "dataset_url": f"https://huggingface.co/datasets/{dataset_repo_id}",
        "model_id": os.getenv("HF_MODEL_ID"),
        "message": "Dataset created and uploaded successfully. Proceed to fine-tune via RunPod."
    }
