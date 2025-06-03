import os
import time
import json
import base64
import requests
from dotenv import load_dotenv
from huggingface_hub import HfApi

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str) -> bool:
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"
    api = HfApi(token=os.getenv('HF_TOKEN'))

    try:
        if upload_dataset(api, dataset_repo_id, dataset_file_path):
            training_result = start_training_pipeline(lora_id, dataset_repo_id)
            return training_result
    finally:
        cleanup(dataset_file_path, api, dataset_repo_id)
    
    return False

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

def start_training_pipeline(lora_id: str, dataset_repo_id: str) -> bool:
    
    # These are the config filepath (you can read from this and put into the pod creation)
    # Also the output_model_path is the path where the model will be saved
    print("🔄 Starting training pipeline...")
    model_output_path = f"output/{lora_id}"
    config_content = generate_config("lora_training_config.yaml", dataset_repo_id, model_output_path)
    
    # In create_pod here is where i should define my docker image and the variables i pass in ...
    pod_id = create_pod(lora_id, dataset_repo_id, model_output_path, config_content)
    if not pod_id:
        return False

    if not wait_for_pod_ready(lora_id):
        return False

    print("✅ Training config uploaded to pod.")
    print("⏳ Waiting for model to appear on HF...")

    for _ in range(60):  # ~30 minutes (60 * 30s)
        if check_lora_model_uploaded(lora_id):
            print("✅ LoRA model found on HF.")
            return True
        time.sleep(30)

    print("❌ Timed out waiting for LoRA model to upload.")
    return False

def create_pod(lora_id: str, dataset_repo_id: str, model_output_path: str, config_content: str) -> str:
    headers = runpod_headers()
    pod_name = f"{lora_id}-trainer"

    query = {"query": "query { gpuTypes { id displayName memoryInGb } }"}
    resp = requests.post("https://api.runpod.io/graphql", json=query, headers=headers).json()
    if "errors" in resp:
        print("❌ Failed to fetch GPU types:", resp["errors"])
        return None

    gpus = sorted([g for g in resp["data"]["gpuTypes"] if g["memoryInGb"] >= 24], key=lambda x: x["memoryInGb"])
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
                "imageName": "docker3randomdude/lora-trainer:latest", # My custom docker image
                "dockerArgs": "",
                "ports": "8888/http",
                "volumeMountPath": "/workspace",
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

def wait_for_pod_ready(lora_id: str, interval=53, retries=30) -> bool:
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

def cleanup(temp_path: str, api: HfApi, dataset_repo_id: str):
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
        print(f"⚠️ Error checking model upload: {e}")
        return False

def runpod_headers():
    return {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }