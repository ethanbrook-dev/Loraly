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

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str) -> dict:
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"
    api = HfApi(token=os.getenv('HF_TOKEN'))

    try:
        if upload_dataset(api, dataset_repo_id, dataset_file_path):
            training_result = start_training_pipeline(lora_id, dataset_repo_id)
            if training_result["status"] == "success":
                return training_result
    finally:
        cleanup(dataset_file_path, api, dataset_repo_id)

    return {"status": "error", "message": "Dataset upload or training failed."}

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

def start_training_pipeline(lora_id: str, dataset_repo_id: str) -> dict:
    pod_id = create_pod(lora_id, dataset_repo_id)
    if not pod_id:
        return {"status": "error", "message": "Failed to create RunPod pod."}

    if not wait_for_pod_ready(lora_id):
        return {"status": "error", "message": "Pod runtime not initialized."}

    config_out = f"lora_training_config_{lora_id}.yaml"
    output_model_path = generate_config("lora_training_config.yaml", config_out, dataset_repo_id)

    if not upload_config_to_pod(pod_id, config_out, "/workspace/fine-tuning/config.yaml"):
        return {"status": "error", "message": "Failed to upload config to pod."}

    print("✅ Training config uploaded to pod.")
    return {"status": "success", "pod_id": pod_id}

def create_pod(lora_id: str, dataset_repo_id: str) -> str:
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
                "imageName": "runpod/llm-finetuning:latest",
                "dockerArgs": "",
                "ports": "8888/http",
                "volumeMountPath": "/workspace",
                "env": [
                    {"key": "HF_TOKEN", "value": os.getenv("HF_TOKEN")},
                    {"key": "HF_USERNAME", "value": os.getenv("HF_USERNAME")},
                    {"key": "BASE_MODEL", "value": os.getenv("HF_MODEL_ID")},
                    {"key": "DATASET_REPO", "value": dataset_repo_id}
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

def generate_config(template_path: str, output_path: str, dataset_repo_id: str) -> str:
    with open(template_path, "r") as f:
        content = f.read()

    model_output_path = "myModelPath"
    replacements = {
        "--BASE_MODEL--": os.getenv("HF_MODEL_ID"),
        "--DATASET_REPO_ID--": dataset_repo_id,
        "--OUTPUT_DIR--": model_output_path
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    with open(output_path, "w") as f:
        f.write(content)

    print(f"✅ Config written: {output_path}")
    return model_output_path

def upload_config_to_pod(pod_id: str, local_path: str, remote_path: str) -> bool:
    if not os.path.exists(local_path):
        print(f"❌ Missing file: {local_path}")
        return False

    try:
        with open(local_path, "rb") as f:
            file_content = f.read()
        encoded_content = base64.b64encode(file_content).decode("utf-8")
    except Exception as e:
        print(f"❌ Failed to read or encode config: {e}")
        return False

    url = f"https://api.runpod.io/v2/{pod_id}/file/upload"
    headers = {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "path": remote_path,
        "file": encoded_content
    }

    print(f"📤 Uploading config to pod {pod_id} as {remote_path}...")
    resp = requests.post(url, headers=headers, json=payload)

    if resp.status_code == 200:
        print("✅ Config file uploaded successfully.")
        return True
    else:
        print(f"❌ Upload failed: {resp.status_code} - {resp.text}")
        return False

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

def runpod_headers():
    return {
        "Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}",
        "Content-Type": "application/json"
    }
