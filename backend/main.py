# main.py - backend entrypoint

# -------------------- Standard library imports --------------------
import asyncio
import json
import os
import re
import tempfile
import traceback
import unicodedata
from contextlib import asynccontextmanager

# -------------------- Third-party imports --------------------
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split 
from supabase import create_client
import modal

# -------------------- Cryptography imports --------------------
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# -------------------- Local imports --------------------
from backend.dataset_analyzer import (
    analyze_dataset,
    get_dataset_analysis_from_supabase,
    save_dataset_analysis_to_supabase,
)
from backend.train_lora import finalize_training, train_lora

# -------------------- FastAPI app --------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local dev
        "https://loralydemo.netlify.app"  # Demo frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Environment variables --------------------
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

# -------------------- Encryption --------------------
RSA_PRIVATE_KEY = os.getenv("RSA_PRIVATE_KEY")
RSA_PUBLIC_KEY = os.getenv("RSA_PUBLIC_KEY")

# -------------------- Supabase client --------------------
supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# -------------------- Root endpoint --------------------
@app.get("/")
async def root():
    return {"message": "Hello from Loraly! This is the backend."}

# -------------------- Finalize training endpoint --------------------
@app.post("/finalize-training")
async def finalize_training_endpoint(request: Request):
    data = await request.json()
    lora_id = data.get("lora_id")
    status = data.get("status")
    repo_url = data.get("repo_url")

    if not lora_id:
        return JSONResponse({"error": "Missing lora_id"}, status_code=400)
    if status not in ["upload_complete", "cuda_not_available", "training_failed"]:
        return JSONResponse({"error": "Invalid status"}, status_code=400)
    if status == "upload_complete" and not repo_url:
        return JSONResponse({"error": "Missing repo_url for upload_complete"}, status_code=400)

    print_from_main(f"Received finalize notification for LoRA {lora_id}")
    
    env_vars = get_env_vars_for_lora(lora_id)
    if not env_vars:
        return JSONResponse({"error": "Creator not found for this LoRA"}, status_code=404)
    runpod_api_key = env_vars["runpod_api_key"]

    try:
        resp = supabase.table("loras").select("pod_id").eq("id", lora_id).single().execute()
        pod_id = resp.data.get("pod_id") if resp.data else None

        if not pod_id:
            print_from_main(f"No pod_id found for LoRA {lora_id}")
            return JSONResponse({"error": "Pod ID not found"}, status_code=404)

        finalize_training(runpod_api_key, lora_id, pod_id, cuda_not_available=(status == "cuda_not_available"))
        return {"status": "success", "message": f"Training finalized for LoRA {lora_id}"}

    except Exception as e:
        print_from_main(f"Error finalizing training: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

# -------------------- Loading modal objects --------------------
Phi2ChatCls = modal.Cls.from_name("phi2-lora-chat", "Phi2Chat")
chat_worker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_worker
    print_from_main("Spinning up PERSISTENT Modal chat worker...")
    
    # Chat worker
    chat_worker = Phi2ChatCls()
    print_from_main(f"Persistent chat worker spawned: {chat_worker}")
    yield
    print_from_main("Terminating persistent worker...")
    chat_worker.shutdown.remote()
    print_from_main("Modal worker terminated.")

app.router.lifespan_context = lifespan

# -------------------- Chat API --------------------
@app.post("/chat")
async def chat(request: Request) -> JSONResponse:
    try:
        data = await request.json()
        lora_id = data.get("loraid")
        chat_history = data.get("chatHistory")

        if not lora_id or not chat_history:
            return JSONResponse({"error": "Missing loraid or chatHistory"}, status_code=400)
        if not isinstance(chat_history, list):
            return JSONResponse({"error": "chatHistory must be a list"}, status_code=400)

        env_vars = get_env_vars_for_lora(lora_id)
        if not env_vars:
            return JSONResponse({"error": "Creator not found for this LoRA"}, status_code=404)
        hf_token = env_vars["hf_token"]
        hf_username = env_vars["hf_username"]

        print_from_main(f"Sending prompt to Modal for LoRA: {lora_id}")

        max_new_tokens, end_prompt, participants = get_dataset_analysis_from_supabase(supabase, lora_id)

        response = chat_worker.chat_with_lora.remote(
            hf_token=hf_token,
            lora_repo=f"{hf_username}/{lora_id}-model",
            chat_history=json.dumps(chat_history),
            max_new_tokens=max_new_tokens,
            end_prompt=end_prompt,
            participants=participants
        )

        return {"response": response}

    except Exception as e:
        print_from_main(f"ERROR in chat endpoint: {str(e)}")
        traceback.print_exc()
        return JSONResponse({"error": "Internal server error"}, status_code=500)


# -------------------- Generate voice endpoint --------------------
@app.post("/generate-voice")
async def generate_voice(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        lora_id = data.get("loraId")
        raw_text = data.get("rawText")
        participants = data.get("participants")

        if not lora_id or not raw_text:
            return JSONResponse({"error": "Missing loraId or rawText"}, status_code=400)

        env_vars = get_env_vars_for_lora(lora_id)
        if not env_vars:
            return JSONResponse({"error": "Creator not found for this LoRA"}, status_code=404)

        # Convert frontend JSONL into Axolotl format
        jsonl_str = text_to_axolotl_json(raw_text)

        # Split train / validation
        train_jsonl, val_jsonl = split_train_val(jsonl_str, val_frac=0.02)

        # ---------- Write temp files ----------
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f_train, \
             tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as f_val:
            f_train_path = f_train.name
            f_val_path = f_val.name
            f_train.write(train_jsonl)
            f_val.write(val_jsonl)
            f_train.flush()
            f_val.flush()

        # ---------- Analyze dataset ----------
        try:
            analysis = analyze_dataset(f_train_path, participants)
            save_dataset_analysis_to_supabase(supabase, lora_id, analysis)
        except Exception as e:
            print_from_main(f"Failed to analyze dataset: {e}")
            analysis = None

        # ---------- Launch training in background ----------
        background_tasks.add_task(
            train_lora,
            env_vars,
            lora_id,
            f_train_path,
            f_val_path,
            "lora_training_configs/lora_training_config_phi2.yaml"
        )
        background_tasks.add_task(delete_file_after_delay, f_train_path, 10)
        background_tasks.add_task(delete_file_after_delay, f_val_path, 10)

        return {
            "status": "processing",
            "message": "Dataset submitted. LoRA fine-tuning will run in the background with validation."
        }

    except Exception as e:
        print_from_main(f"ERROR in generate-voice endpoint: {str(e)}")
        traceback.print_exc()
        return JSONResponse({"error": "Internal server error"}, status_code=500)

# -------------------- Save env vars endpoint --------------------
@app.post("/save-env-vars")
async def save_env_vars(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        hf_token = data.get("hf_token")
        hf_username = data.get("hf_username")
        runpod_api_key = data.get("runpod_api_key")

        if not user_id or not hf_token or not hf_username or not runpod_api_key:
            return JSONResponse({"error": "Missing required fields"}, status_code=400)

        # Serialize env vars into JSON string
        env_blob = json.dumps({
            "hf_token": hf_token,
            "hf_username": hf_username,
            "runpod_api_key": runpod_api_key
        })

        # Load public key for encryption
        public_key = serialization.load_pem_public_key(RSA_PUBLIC_KEY.encode())

        encrypted = public_key.encrypt(
            env_blob.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Base64 encode for DB storage
        encrypted_b64 = base64.b64encode(encrypted).decode()

        resp = supabase.table("profiles").update({
            "env_vars_encrypted": encrypted_b64
        }).eq("id", user_id).execute()

        print_from_main(f"Supabase response: {resp}")

        if not resp.data:
            return JSONResponse({"error": "Failed to update profiles table"}, status_code=500)

        return {"status": "success", "message": "API keys saved successfully"}

    except Exception as e:
        print_from_main(f"Error saving env vars: {e}")
        traceback.print_exc()
        return JSONResponse({"error": "Internal server error"}, status_code=500)

# -------------------- Helpers --------------------
async def delete_file_after_delay(file_path: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print_from_main(f"Temp file deleted: {file_path}")
    except Exception as e:
        print_from_main(f"Error deleting temp file: {e}")

def split_train_val(jsonl_str: str, val_frac: float = 0.02) -> tuple[str, str]:
    lines = [line for line in jsonl_str.strip().splitlines() if line.strip()]
    train_lines, val_lines = train_test_split(lines, test_size=val_frac, random_state=42)
    return "\n".join(train_lines), "\n".join(val_lines)

def clean_unicode(text: str) -> str:
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...", "•": "-", " ": " ", "\u00A0": " "
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return unicodedata.normalize('NFKC', text)

def remove_all_unicode_except_ascii(text: str) -> str:
    allowed_chars = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        " ~!@#$%^&*()-=_+[]{};':\"\\|,.<>/?"
    )
    return "".join(c for c in text if c in allowed_chars)

def text_to_axolotl_json(raw_text: str) -> str:
    conversation_jsonl = []
    for line in raw_text.strip().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            text = remove_all_unicode_except_ascii(clean_unicode(obj.get("text", "").strip()))
            pattern = r"(User|Assistant):\s*(.*?)(?=(User|Assistant):|$)"
            matches = re.findall(pattern, text, flags=re.DOTALL)
            messages = []
            for match in matches:
                role = "user" if match[0].lower() == "user" else "assistant"
                content = match[1].strip()
                if content:
                    messages.append({"role": role, "content": content})
            if messages:
                conversation_jsonl.append(json.dumps({"messages": messages}, ensure_ascii=False))
        except Exception:
            continue
    return "\n".join(conversation_jsonl)

def print_from_main(message: str):
    print(f"[MAIN.PY] {message}")

def fetch_env_vars_for_user(user_id: str) -> dict:
    resp = supabase.table("profiles").select("env_vars_encrypted").eq("id", user_id).single().execute()

    if not resp.data or not resp.data.get("env_vars_encrypted"):
        raise ValueError("No env vars found for this user")

    encrypted_b64 = resp.data["env_vars_encrypted"]
    encrypted_bytes = base64.b64decode(encrypted_b64)

    private_key = serialization.load_pem_private_key(
        RSA_PRIVATE_KEY.encode(),
        password=None,
    )

    decrypted = private_key.decrypt(
        encrypted_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return json.loads(decrypted.decode())

def get_env_vars_for_lora(lora_id: str) -> dict | None:
    lora_row = supabase.table("loras").select("creator_id").eq("id", lora_id).single().execute()
    if not lora_row.data or not lora_row.data.get("creator_id"):
        return None

    creator_id = lora_row.data["creator_id"]
    return fetch_env_vars_for_user(creator_id)
