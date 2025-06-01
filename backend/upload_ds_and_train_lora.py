import json
import os
import requests
import time
from huggingface_hub import HfApi
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

def upload_ds_and_train_lora(lora_id: str, dataset_file_path: str) -> dict:
    dataset_repo_id = f"{os.getenv('HF_USERNAME')}/{lora_id}-dataset"
    api = HfApi(token=os.getenv('HF_TOKEN'))

    try:
        if upload_ds_to_hf(api, dataset_repo_id, dataset_file_path):
            lora_trained = train_lora_via_runpod(lora_id, dataset_repo_id)
            # Optionally return here if success path doesn't need delete+cleanup:
            # return lora_trained

        try:
            api.delete_repo(repo_id=dataset_repo_id, repo_type="dataset")
            print("✅ Dataset repo deleted successfully.")
        except Exception as e:
            print(f"❌ Failed to delete dataset repo: {e}")

        return {"status": "error", "message": "Dataset upload failed or training not triggered."}

    finally:
        try:
            os.remove(dataset_file_path)
            print(f"🧹 Deleted temp dataset file: {dataset_file_path}")
        except Exception as e:
            print(f"⚠️ Failed to delete temp dataset file: {e}")


def upload_ds_to_hf(api, dataset_repo_id: str, dataset_file_path: str) -> bool:
    try:
        api.create_repo(repo_id=dataset_repo_id, repo_type="dataset", private=True, exist_ok=True)
        print("✅ Private dataset repo created (or already exists).")
    except Exception as e:
        print(f"❌ Failed to create dataset repo: {e}")
        return False

    try:
        api.upload_file(
            path_or_fileobj=dataset_file_path,
            path_in_repo="data.jsonl",
            repo_id=dataset_repo_id,
            repo_type="dataset"
        )
        print("✅ Dataset uploaded successfully.")
        return True
    except Exception as e:
        print(f"❌ Failed to upload dataset file: {e}")
        return False

def train_lora_via_runpod(lora_id: str, dataset_repo_id: str) -> dict:
    pod_id = create_runpod_training_pod(lora_id, dataset_repo_id)
    if pod_id is None:
        return {"status": "error", "message": "Failed to create pod"}

    if not wait_for_pod_to_start(pod_name=f"{lora_id}-trainer", retryInSec=10):
        return {"status": "error", "message": "Pod logs did not show training start."}

    print("✅ Pod ready and training environment initialized.")
    return {"status": "success", "pod_id": pod_id}

def create_runpod_training_pod(lora_id: str, dataset_repo_id: str) -> str:
    pod_name = f"{lora_id}-trainer"
    image_name = "runpod/llm-finetuning:latest"

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

    if "errors" in data:
        print("❌ Error fetching GPU types:", data["errors"])
        return None

    gpus = data["data"]["gpuTypes"]
    eligible_gpus = sorted([g for g in gpus if g["memoryInGb"] >= 24], key=lambda x: x["memoryInGb"])
    if not eligible_gpus:
        print("❌ No suitable GPUs (≥24GB) found.")
        return None

    for gpu in eligible_gpus:
        print(f"🔍 Trying GPU: {gpu['displayName']} ({gpu['id']}) with {gpu['memoryInGb']} GB")

        env_vars = [
            {"key": "HF_TOKEN", "value": os.getenv('HF_TOKEN')},
            {"key": "HF_USERNAME", "value": os.getenv('HF_USERNAME')},
            {"key": "BASE_MODEL", "value": os.getenv('HF_MODEL_ID')},
            {"key": "DATASET_REPO", "value": dataset_repo_id}
        ]

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
                "imageName": image_name,
                "dockerArgs": "",
                "ports": "8888/http",
                "volumeMountPath": "/workspace",
                "env": env_vars
            }
        }

        create_response = requests.post(
            "https://api.runpod.io/graphql",
            json={
                "query": """
                mutation PodFindAndDeployOnDemand($input: PodFindAndDeployOnDemandInput!) {
                    podFindAndDeployOnDemand(input: $input) {
                        id
                    }
                }
                """,
                "variables": {"input": payload["input"]}
            },
            headers=headers
        )

        pod_data = create_response.json()
        if "errors" in pod_data:
            print(f"❌ Failed to create pod with {gpu['displayName']}: {pod_data['errors']}")
            continue
        pod_id = pod_data["data"]["podFindAndDeployOnDemand"]["id"]
        print(f"✅ Pod created with {gpu['displayName']}: {pod_id}")
        return pod_id

    print("❌ All eligible GPUs failed to create pod.")
    return None

def wait_for_pod_to_start(pod_name: str, retryInSec: int, maxRuntimeChecks: int = 5) -> bool:
    headers = {"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"}
    pod_id = None

    # Step 1: Wait for pod to appear
    print("⏳ Waiting for pod to appear...")
    while not pod_id:
        response = requests.post("https://api.runpod.io/graphql", json={
            "query": """
                query {
                    myself {
                        pods {
                            id
                            name
                        }
                    }
                }
            """
        }, headers=headers)
        data = response.json()

        for pod in data.get("data", {}).get("myself", {}).get("pods", []):
            print(f"POD: {pod['name']} (id: {pod['id']})")
            if pod["name"] == pod_name:
                pod_id = pod["id"]
                break

        if not pod_id:
            print(f"🔄 Pod not found yet, retrying in {retryInSec}s...")
            time.sleep(retryInSec)

    print(f"✅ Found pod: {pod_id}")

    # Step 2: Poll pod info via GraphQL
    print("🔄 Monitoring pod status...")

    count = 1
    while count < maxRuntimeChecks:
        print(f"\n🔄 Fetching pods info ({count}/{maxRuntimeChecks})")

        query = {
            "query": """
            query Pods {
            myself {
                pods {
                id
                name
                runtime {
                    uptimeInSeconds
                    ports {
                    ip
                    isIpPublic
                    privatePort
                    publicPort
                    type
                    }
                    gpus {
                    id
                    gpuUtilPercent
                    memoryUtilPercent
                    }
                    container {
                    cpuPercent
                    memoryPercent
                    }
                }
                }
            }
            }
            """
        }

        response = requests.post("https://api.runpod.io/graphql", json=query, headers=headers)
        data = response.json()

        pods = data.get("data", {}).get("myself", {}).get("pods", [])
        for pod in pods:
            if pod["name"] == pod_name and pod.get("runtime") is not None:
                print("✅ Runtime is now available.")
                return True

        print(f"⏳ Runtime not ready yet. Sleeping for {retryInSec} seconds...\n")
        time.sleep(retryInSec)
        count += 1
    print("❌ Pod runtime did not become available in time.")

