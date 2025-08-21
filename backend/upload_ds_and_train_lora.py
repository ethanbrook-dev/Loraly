# The python training script (starting a pod, training, closing the pod, ... , checking hf)

import os
import time
import requests
from dotenv import load_dotenv
from huggingface_hub import HfApi
from supabase import create_client
from enum import Enum
from datetime import datetime

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

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str):
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"
    api = HfApi(token=os.getenv('HF_TOKEN'))
    pod_id = None
    
    update_lora_status(lora_id, LoraStatus.TRAINING)

    try:
        if upload_dataset(api, dataset_repo_id, dataset_file_path):
            training_successfull, pod_id = start_training_pipeline(lora_id, dataset_repo_id)
            if training_successfull:
                add_created_lora_to_user(lora_id) # Add the LoRA to the creator’s profile in Supabase
                update_lora_status(lora_id, LoraStatus.TRAINING_COMPLETED)
            else:
                update_lora_status(lora_id, LoraStatus.TRAINING_FAILED)
    finally:
        cleanup(dataset_file_path, api, dataset_repo_id, lora_id)
        if pod_id:
            delete_pod(pod_id)
    
    return

def upload_dataset(api: HfApi, repo_id: str, file_path: str) -> bool:
    try:
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo="data.jsonl",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print("✅ Dataset uploaded.")
        return True
    except Exception as e:
        print(f"❌ Dataset upload failed: {e}")
        return False

def start_training_pipeline(lora_id: str, dataset_repo_id: str) -> tuple[bool, str | None]:
    
    training_start = datetime.now()
    
    # These are the config filepath (you can read from this and put into the pod creation)
    # Also the output_model_path is the path where the model will be saved
    print("🔄 Starting training pipeline...")
    model_output_path = f"output/{lora_id}"
    config_content = generate_config("lora_training_config.yaml", dataset_repo_id, model_output_path)
    
    pod_id = create_pod(lora_id, dataset_repo_id, model_output_path, config_content)
    if not pod_id:
        return False, None

    if not wait_for_pod_ready(lora_id):
        return False, pod_id

    print("✅ Training config uploaded to pod.")
    print("⏳ Waiting for model to appear on HF...")

    max_hours = 24 # Allow a full day of training till timeout
    hours_to_wait = 2
    seconds_to_wait = hours_to_wait * 3600  # 7200 seconds = 2 hours
    count = 0

    while count * hours_to_wait < max_hours:
        if check_lora_model_uploaded(lora_id):
            print("✅ LoRA model found on HF.")
            
            training_end = datetime.now()
            duration = training_end - training_start
            hours = duration.total_seconds() / 3600
            
            print(f"🕒 LoRA took {hours:.2f} hours to train.")
            return True, pod_id
        
        print(f"⚙️ LoRA has been training for {count * hours_to_wait} hours now.")
        time.sleep(seconds_to_wait)
        count += 1

    # If max wait is hit:
    print(f"⏰ LoRA model training timeout of {max_hours} hours reached.")
    return False, pod_id


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
                    {"key": "MODEL_OUTPUT_DIR", "value": model_output_path}
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

def cleanup(temp_path: str, api: HfApi, dataset_repo_id: str, lora_id: str):
    print("🧹 Cleaning up...")
    try:
        os.remove(temp_path)
        print(f"🧹 Deleted local dataset: {temp_path}")
    except Exception as e:
        print(f"⚠️ Failed to delete local file: {e}")

    try:
        api.delete_repo(repo_id=dataset_repo_id, repo_type="dataset")
        print("🧼 Deleted HF dataset repo.")
    except Exception as e:
        print(f"⚠️ Failed to delete HF dataset repo: {e}")

def check_lora_model_uploaded(lora_id: str) -> bool:
    model_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-model" # DO NOT CHANGE THIS -> the docker image will create this repo
    api = HfApi(token=os.getenv('HF_TOKEN'))

    try:
        files = api.list_repo_files(repo_id=model_repo_id, repo_type="model")
        return any(
            "adapter" in f or 
            "pytorch_model" in f or 
            f.endswith(".safetensors") 
            for f in files
        )
    except Exception as e:
        print(f"❌ HuggingFace Model not found yet ... waiting ...")
        return False

def delete_pod(pod_id: str):
    url = f"https://rest.runpod.io/v1/pods/{pod_id}"
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"
    }

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
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

