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
from sklearn.model_selection import train_test_split

# -------------------- Third-party imports --------------------
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import modal
from supabase import create_client
from dotenv import load_dotenv

# -------------------- Local imports --------------------
from backend.dataset_analyzer import analyze_dataset, save_dataset_analysis_to_supabase, get_dataset_analysis_from_supabase
from backend.augment_dataset_using_gpt import augment_dataset_with_gpt
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
load_dotenv(dotenv_path=".env.local")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_USERNAME = os.getenv("HF_USERNAME")

if not HF_TOKEN:
    raise RuntimeError("❌ HF_TOKEN not found in environment. Please set it in .env.local")
if not HF_USERNAME:
    raise RuntimeError("❌ HF_USERNAME not found in environment. Please set it in .env.local")

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

    print(f"🟢 Received finalize notification for LoRA {lora_id}")

    try:
        resp = supabase.table("loras").select("pod_id").eq("id", lora_id).single().execute()
        pod_id = resp.data.get("pod_id") if resp.data else None

        if not pod_id:
            print(f"⚠️ No pod_id found for LoRA {lora_id}")
            return JSONResponse({"error": "Pod ID not found"}, status_code=404)

        finalize_training(lora_id, pod_id, cuda_not_available=(status == "cuda_not_available"))
        return {"status": "success", "message": f"Training finalized for LoRA {lora_id}"}

    except Exception as e:
        print(f"❌ Error finalizing training: {e}")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

# -------------------- Loading modal objects --------------------
Phi2ChatCls = modal.Cls.from_name("phi2-lora-chat", "Phi2Chat")
chat_worker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_worker
    print("🔌 Spinning up PERSISTENT Modal chat worker...")
    
    # Chat worker
    chat_worker = Phi2ChatCls(hf_token=HF_TOKEN)
    print(f"✔️ Persistent chat worker spawned: {chat_worker}")
    
    yield
    print("👋 Terminating persistent worker...")
    chat_worker.shutdown.remote()
    print("✔️ Modal worker terminated.")

app.router.lifespan_context = lifespan

# -------------------- Chat API --------------------

@app.post("/chat")
async def chat(request: Request) -> JSONResponse:
    data = await request.json()
    loraid = data.get("loraid")
    chatHistory = data.get("chatHistory")

    if not loraid or not chatHistory:
        return JSONResponse({"error": "Missing loraid or chatHistory"}, status_code=400)

    try:
        print("🚀 Sending prompt to Modal...")
        max_new_tokens, end_prompt, participants = get_dataset_analysis_from_supabase(supabase, loraid)
        response = chat_worker.chat_with_lora.remote(
            lora_repo=f"{HF_USERNAME}/{loraid}-model",
            chat_history=json.dumps(chatHistory),
            max_new_tokens=max_new_tokens,
            end_prompt=end_prompt,
            participants=participants
        )
        return {"response": response}

    except Exception as e:
        print("❌ ERROR GETTING RESPONSE")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

# -------------------- Generate voice endpoint --------------------
@app.post("/generate-voice")
async def generate_voice(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    lora_id = data.get("loraId")
    raw_text = data.get("rawText")
    participants = data.get("participants")

    if not lora_id or not raw_text:
        return JSONResponse({"error": "Missing loraId or rawText"}, status_code=400)

    # Convert frontend JSONL into Axolotl format
    jsonl_str = text_to_axolotl_json(raw_text)
    
    words = int(input("Enter target word count for augmentation (e.g., 600000): "))
    
    augmented_jsonl_str = augment_dataset_with_gpt(jsonl_str, target_words=words)

    # Split train / validation
    train_jsonl, val_jsonl = split_train_val(augmented_jsonl_str, val_frac=0.02)

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
        print(f"⚠️ Failed to analyze dataset: {e}")
        analysis = None

    # ---- FOR DEV ---- TODO
    config_path = "lora_training_configs/lora_training_config_phi2.yaml" # Default is phi2
    choice = int(input("\n\n-----\nChoose training config:\n1. phi2\n2. Llama3.1-8B\n"))
    if choice == 2:
        config_path = "lora_training_configs/lora_training_config_llama8B.yaml"
        
    print(f"> Using config: {config_path}")
    input("Press Enter to continue...")

    # ---------- Launch training in background ----------
    background_tasks.add_task(train_lora, lora_id, f_train_path, f_val_path, config_path)
    background_tasks.add_task(delete_file_after_delay, f_train_path, 10)
    background_tasks.add_task(delete_file_after_delay, f_val_path, 10)

    return {
        "status": "processing",
        "message": "Dataset submitted. LoRA fine-tuning will run in the background with validation."
    }

# -------------------- Helpers --------------------
async def delete_file_after_delay(file_path: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🧹 Temp file deleted: {file_path}")
    except Exception as e:
        print(f"⚠️ Error deleting temp file: {e}")

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
