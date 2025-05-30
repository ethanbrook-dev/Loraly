# --- create_runpod_job.py ---
import requests
import base64
import json

def create_runpod_job(runpod_api_key, jsonl_str, config_yaml_str, hf_token, lora_id):
    RUNPOD_ENDPOINT = "https://api.runpod.io/graphql"

    # Encode your dataset and config in base64
    encoded_jsonl = base64.b64encode(jsonl_str.encode()).decode()
    encoded_config = base64.b64encode(config_yaml_str.encode()).decode()
    encoded_hf_token = base64.b64encode(hf_token.encode()).decode()

    # Script to run inside RunPod container
    start_script = f"""
apt-get update && apt-get install -y git-lfs
pip install -q bitsandbytes==0.45.4 accelerate==0.27.2
pip install -q -U git+https://github.com/OpenAccess-AI-Collective/axolotl.git
pip install triton
pip install --upgrade transformers peft

# Decode input files
mkdir -p /workspace/data
mkdir -p /workspace/configs
echo "{encoded_jsonl}" | base64 -d > /workspace/data/neatjsonltextfile.jsonl
echo "{encoded_config}" | base64 -d > /workspace/configs/myLoRA_training.yaml
echo "{encoded_hf_token}" | base64 -d > hf.token

# Login to Hugging Face
huggingface-cli login --token $(cat hf.token)

# Run Axolotl training
cd /workspace
axolotl prepare /workspace/configs/myLoRA_training.yaml
axolotl train /workspace/configs/myLoRA_training.yaml

# Upload results to Hugging Face
python3 -c '
from huggingface_hub import HfApi
api = HfApi()
api.create_repo(repo_id="{lora_id}", private=True, exist_ok=True)
api.upload_file(path_or_fileobj="lora_output/adapter_model.safetensors", path_in_repo="adapter_model.safetensors", repo_id="{lora_id}")
api.upload_file(path_or_fileobj="configs/myLoRA_training.yaml", path_in_repo="config.yaml", repo_id="{lora_id}")
'
"""

    payload = {
        "query": """
        mutation {
            podFindAndDeployOnDemand(input: {
                cloudType: ALL,
                gpuCount: 1,
                gpuTypeId: "NVIDIA A100",
                containerDiskInGb: 20,
                volumeInGb: 10,
                ports: [],
                name: "lora-train-{lora_id}",
                dockerArgs: "",
                imageName: "python:3.10-slim",
                startCommand: """ + json.dumps(start_script) + """
            }) {
                id
                podId
                environmentId
                onDemandInstanceId
            }
        }
        """
    }

    headers = {
        "Authorization": f"Bearer {runpod_api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(RUNPOD_ENDPOINT, headers=headers, json=payload)
    return response.json()