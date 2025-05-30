from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, json
from create_runpod_job import create_runpod_job

# Load environment variables
load_dotenv('.env.local')
hf_token = os.getenv("NEXT_PUBLIC_HF_TOKEN")
runpod_api_key = os.getenv("RUNPOD_API_KEY")

app = FastAPI()

origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-voice")
async def generate_voice(request: Request):
    data = await request.json()
    lora_id = data.get("loraId")
    text = data.get("rawText")
    email = data.get("userEmail")
    
    if not all([hf_token, runpod_api_key]):
        return {"status": "error", "message": "API keys not set."}

    print("Received LoRA training request:")
    print("LoRA ID:", lora_id)
    print("Email:", email)

    # Step 1: Convert to jsonl string
    jsonl_str = text_to_jsonl_string(text)

    # Step 2: Generate YAML config
    config_yaml_str = generate_yaml_config(lora_id)

    # Step 3: Send job to RunPod
    runpod_response = create_runpod_job(
        runpod_api_key=runpod_api_key,
        jsonl_str=jsonl_str,
        config_yaml_str=config_yaml_str,
        hf_token=hf_token,
        lora_id=lora_id
    )

    print("RunPod response:", runpod_response)

    return {
        "status": "submitted",
        "message": "Training job submitted to RunPod.",
        "runpod_response": runpod_response
    }

def text_to_jsonl_string(raw_text: str) -> str:
    sentences = raw_text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    lines = [json.dumps({"text": sentence + "."}, ensure_ascii=False) for sentence in sentences]
    return "\n".join(lines)

def generate_yaml_config(lora_id: str) -> str:
    return f"""base_model: mistralai/Mistral-7B-Instruct-v0.3
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer
load_in_8bit: true

gradient_checkpointing: true

datasets:
  - path: /workspace/data/neatjsonltextfile.jsonl
    type: completion

dataset_prepared_path: last_run_prepared

val_set_size: 0.01
output_dir: /workspace/lora_output
sequence_len: 512
pad_to_sequence_len: true
adapter: lora

lora_r: 8
lora_alpha: 16
lora_dropout: 0.05
lora_target_modules: 
  - q_proj
  - v_proj
  - k_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj

lr_scheduler: cosine
learning_rate: 0.0003
micro_batch_size: 2
gradient_accumulation_steps: 4
epochs: 3
optimizer: adamw_bnb_8bit
"""
