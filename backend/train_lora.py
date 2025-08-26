# The python training script (starting a pod, training, closing the pod, ... , checking hf)

import os
import time
import requests
from dotenv import load_dotenv
from huggingface_hub import HfApi
from supabase import create_client
from enum import Enum

class LoraStatus(str, Enum):
    TRAINING = "training"
    TRAINING_COMPLETED = "training completed"
    TRAINING_FAILED = "training failed"

# Table names
TABLE_LORAS = "loras"
TABLE_PROFILES = "profiles"

# Column names in 'loras' table
COL_LORA_ID = "id"
COL_LORA_STATUS = "training_status"
COL_CREATOR_ID = "creator_id"

# Column names in 'profiles' table
COL_PROFILE_ID = "id"
COL_LORAS_CREATED = "loras_created"

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)
supabase = create_client(os.getenv('NEXT_PUBLIC_SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# ----------- GLOBAL HfApi INSTANCE -----------
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("❌ HF_TOKEN not found in environment")

api = HfApi(token=HF_TOKEN)

def train_lora(lora_id: str, dataset_file_path: str):
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"
    update_lora_status(lora_id, LoraStatus.TRAINING)

    try:
        upload_dataset_to_hf(dataset_file_path, dataset_repo_id)
        pod_id = start_training_pipeline(lora_id, dataset_repo_id)
        
        if not pod_id:
            print("❌ Failed to start training pipeline.")
            update_lora_status(lora_id, LoraStatus.TRAINING_FAILED)
            cleanup(dataset_file_path)
            return
        
        _ = supabase.table(TABLE_LORAS).update({"pod_id": pod_id}).eq(COL_LORA_ID, lora_id).execute()
        print(f"✅ Pod ID {pod_id} saved to database for LoRA {lora_id}.")
        
    except Exception as e:
        print(f"❌ Training pipeline error: {e}")
        update_lora_status(lora_id, LoraStatus.TRAINING_FAILED)
        cleanup(dataset_file_path)

def finalize_training(lora_id: str, pod_id: str):
    """Called when backend notifies us training finished. Checks HF, updates DB, and cleans up."""

    print("⏳ Checking if LoRA model is available on Hugging Face...")
    if check_lora_model_uploaded(lora_id):
        print(f"✅ LoRA model {lora_id} found on Hugging Face.")
        add_created_lora_to_user(lora_id)
        update_lora_status(lora_id, LoraStatus.TRAINING_COMPLETED)
    else:
        print(f"❌ LoRA model {lora_id} not found on Hugging Face.")
        update_lora_status(lora_id, LoraStatus.TRAINING_FAILED)

    if pod_id:
        delete_pod(pod_id)

def upload_dataset_to_hf(dataset_file_path: str, dataset_repo_id: str):
    try:
        api.create_repo(repo_id=dataset_repo_id, repo_type="dataset", exist_ok=True)
        api.upload_file(
            path_or_fileobj=dataset_file_path,
            path_in_repo="data.jsonl",
            repo_id=dataset_repo_id,
            repo_type="dataset"
        )
        print(f"✅ Uploaded dataset to {dataset_repo_id}")
    except Exception as e:
        print(f"❌ Failed to upload dataset: {e}")
        raise

def cleanup(temp_path: str):
    print("🧹 Cleaning up...")
    try:
        os.remove(temp_path)
        print(f"🧹 Deleted local dataset: {temp_path}")
    except Exception as e:
        print(f"⚠️ Failed to delete local file: {e}")
        
def get_config_template(model_id: str) -> str:
    """Return the correct config template based on the model ID"""
    if "phi" in model_id.lower():
        return "lora_training_config_phi2.yaml"
    elif "mistral" in model_id.lower():
        return "lora_training_config_mistral.yaml"
    else:
        # Default to Mistral config for safety
        return "lora_training_config_mistral.yaml"
    
def start_training_pipeline(lora_id: str, dataset_repo_id: str) -> str | None:
    
    model_id = os.getenv("HF_MODEL_ID")
    config_template = get_config_template(model_id)
    
    # Build the full path to the config file
    configs_dir = "lora_training_configs"
    config_template_path = os.path.join(configs_dir, config_template)
    
    print(f"📋 Using config template: {config_template_path} for model: {model_id}")
    
    # Check if the config file actually exists
    if not os.path.exists(config_template_path):
        print(f"❌ ERROR: Config template file not found at: {config_template_path}")
        print("   Please make sure the file exists in the lora_training_configs folder.")
        return None
    
    print("🔄 Starting training pipeline...")
    model_output_path = f"output/{lora_id}"
    config_content = generate_config(config_template_path, dataset_repo_id, model_output_path)
    
    pod_id = create_pod(lora_id, dataset_repo_id, model_output_path, config_content)
    if not pod_id:
        return None

    if not wait_for_pod_ready(lora_id):
        return pod_id

    print(f"✅ Pod {pod_id} is ready and training has started.")
    return pod_id


def create_pod(lora_id: str, dataset_repo_id: str, model_output_path: str, config_content: str) -> str:
    headers = runpod_headers()
    pod_name = f"{lora_id}-trainer"

    query = {"query": "query { gpuTypes { id displayName memoryInGb } }"}
    resp = requests.post("https://api.runpod.io/graphql", json=query, headers=headers).json()
    if "errors" in resp:
        print("❌ Failed to fetch GPU types:", resp["errors"])
        return None

    gpus = sorted([g for g in resp["data"]["gpuTypes"] if g["memoryInGb"] >= 40], key=lambda x: x["memoryInGb"])
    if not gpus:
        print("❌ No eligible GPUs found.")
        return None

    for gpu in gpus:
        print(f"🔍 Trying GPU: {gpu['displayName']} ({gpu['memoryInGb']} GB)")
        payload = {
            "input": {
                "cloudType": "ALL",
                "gpuCount": 1,
                "volumeInGb": 40,
                "containerDiskInGb": 40,
                "minVcpuCount": 2,
                "minMemoryInGb": 15,
                "gpuTypeId": gpu["id"],
                "name": pod_name,
                "imageName": "docker3randomdude/lt-image-v3:latest",
                "dockerArgs": "",
                "ports": "8888/http",
                "volumeMountPath": "/data",
                "env": [
                    {"key": "HF_TOKEN", "value": os.getenv("HF_TOKEN")},
                    {"key": "HF_USERNAME", "value": os.getenv("HF_USERNAME")},
                    {"key": "BASE_MODEL", "value": os.getenv("HF_MODEL_ID")},
                    {"key": "DATASET_REPO", "value": dataset_repo_id},
                    {"key": "LORA_ID", "value": lora_id},
                    {"key": "CONFIG_CONTENT", "value": config_content},
                    {"key": "MODEL_OUTPUT_DIR", "value": model_output_path},
                    {"key": "BACKEND_NOTIFY_URL", "value": f"{os.getenv('NEXT_PUBLIC_PYTHON_BACKEND_URL')}/finalize-training"}
                ]
            }
        }

        create_resp = requests.post("https://api.runpod.io/graphql", headers=headers, json={
            "query": """
            mutation PodFindAndDeployOnDemand($input: PodFindAndDeployOnDemandInput!) {
                podFindAndDeployOnDemand(input: $input) { id }
            }
            """,
            "variables": {"input": payload["input"]}
        }).json()

        if "errors" in create_resp:
            print(f"❌ Pod creation failed for {gpu['displayName']}: {create_resp['errors']}")
            continue

        pod_id = create_resp["data"]["podFindAndDeployOnDemand"]["id"]
        print(f"✅ Pod created: {pod_id}")
        return pod_id

    return None

def wait_for_pod_ready(lora_id: str, interval=100, retries=30) -> bool:
    headers = runpod_headers()
    pod_name = f"{lora_id}-trainer"

    print("⏳ Waiting for pod to be listed...")
    pod_id = None
    while not pod_id:
        resp = requests.post("https://api.runpod.io/graphql", headers=headers, json={
            "query": "query { myself { pods { id name } } }"
        }).json()
        for pod in resp.get("data", {}).get("myself", {}).get("pods", []):
            if pod["name"] == pod_name:
                pod_id = pod["id"]
                break
        if not pod_id:
            print(f"🔄 Pod not found. Retrying in {interval}s...")
            time.sleep(interval)

    print(f"✅ Pod found: {pod_id}\n⏳ Waiting for runtime...")

    for i in range(retries):
        print(f"🔄 Runtime check ({i+1}/{retries})")
        resp = requests.post("https://api.runpod.io/graphql", headers=headers, json={
            "query": """
            query {
                myself {
                    pods {
                        name
                        runtime { uptimeInSeconds }
                    }
                }
            }
            """
        }).json()
        pods = resp.get("data", {}).get("myself", {}).get("pods", [])
        for pod in pods:
            if pod["name"] == pod_name and pod.get("runtime"):
                print("✅ Runtime is ready.")
                return True
        time.sleep(interval)

    print("❌ Runtime not ready in time.")
    return False

def generate_config(template_path: str, dataset_repo_id: str, model_output_path: str) -> str:
    with open(template_path, "r") as f:
        content = f.read()

    replacements = {
        "--BASE_MODEL--": os.getenv("HF_MODEL_ID"),
        "--DATASET_REPO_ID--": dataset_repo_id,
        "--OUTPUT_DIR--": model_output_path
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    return content

import time

def check_lora_model_uploaded(lora_id: str) -> bool:
    model_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-model"  # DO NOT CHANGE THIS -> the docker image will create this repo
    print(f"🔍 Checking if LoRA model {model_repo_id} exists on HuggingFace...")

    for attempt in range(2):
        try:
            files = api.list_repo_files(repo_id=model_repo_id, repo_type="model")
            found = any(
                "adapter" in f or 
                "pytorch_model" in f or 
                f.endswith(".safetensors") 
                for f in files
            )
            if found:
                print(f"✅ LoRA model {lora_id} found on HuggingFace.")
                return True
            else:
                print(f"⚠️ LoRA model not found on attempt {attempt + 1}.")
        except Exception as e:
            print(f"❌ Error checking LoRA model on attempt {attempt + 1}: {e}")

        if attempt == 0:
            print("⏳ Waiting 60 seconds before retrying...")
            time.sleep(60)

    print(f"❌ LoRA model {lora_id} not found after 2 attempts.")
    return False

def delete_pod(pod_id: str):
    url = f"https://rest.runpod.io/v1/pods/{pod_id}"
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"
    }

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code in (200, 204):
            print(f"🗑️ Pod deleted successfully: {pod_id}")
        else:
            print(f"⚠️ Failed to delete pod: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"⚠️ Exception while deleting pod: {e}")

def runpod_headers():
    return {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }

def add_created_lora_to_user(lora_id: str):
    
    try :
        # 1. Get the creator_id for this lora_id from loras table
        creator_resp = supabase.table(TABLE_LORAS).select(COL_CREATOR_ID).eq(COL_LORA_ID, lora_id).single().execute()
        creator_id = creator_resp.data[COL_CREATOR_ID]

        # 2. Fetch current loras_created array from profiles table for the creator
        profile_resp = supabase.table(TABLE_PROFILES).select(COL_LORAS_CREATED).eq(COL_PROFILE_ID, creator_id).single().execute()

        current_array = profile_resp.data.get(COL_LORAS_CREATED, []) or []

        # 3. Append new lora_id if not already in the array (to avoid duplicates)
        if lora_id not in current_array:
            new_array = current_array + [lora_id]
        else:
            print(f"🗒️ LoRA {lora_id} already exists in user {creator_id}'s loras_created array.")
            return

        # 4. Update the profile with the new array
        update_resp = supabase.table(TABLE_PROFILES).update({COL_LORAS_CREATED: new_array}).eq(COL_PROFILE_ID, creator_id).execute()
    except Exception as e:
        print(f"⚠️ Error adding LoRA {lora_id} to user profile: {e}")
        return

def update_lora_status(lora_id: str, new_status: str):
    _ = supabase.table(TABLE_LORAS).update({COL_LORA_STATUS: new_status}).eq(COL_LORA_ID, lora_id).execute()

