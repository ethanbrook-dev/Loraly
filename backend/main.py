# main.py - the entrypoint for the backend

# Standard library imports
import os
import json
import tempfile
import re
import unicodedata
import traceback
from contextlib import asynccontextmanager

# Third-party imports (api, modal, etc)
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import modal, asyncio
from supabase import create_client

# Local imports
from backend.dataset_analyzer import analyze_dataset
from backend.train_lora import train_lora

# Load supabase
supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://loralydemo.netlify.app"], # frontend URL for demo site
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

HF_TOKEN = os.getenv("HF_TOKEN")
HF_USERNAME = os.getenv("HF_USERNAME")

if not HF_TOKEN:
    raise RuntimeError("❌ HF_TOKEN not found in environment. Please set it in .env.local")
if not HF_USERNAME:
    raise RuntimeError("❌ HF_USERNAME not found in environment. Please set it in .env.local")

# ------------------------------------ TO CHECK BACKEND ON WEB (FOR DEMO SITE) ------------------------------------ #
@app.get("/")
async def root():
    return {"message": "Hello from Loraly! This is the backend."}

# ------------------------------------------------- CHATTING API ------------------------------------------------- #
# 🔁 Correct way to hydrate class from deployed Modal App
Phi2ChatCls = modal.Cls.from_name("phi2-lora-chat", "Phi2Chat")

chat_worker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_worker
    print("🔌 Spinning up PERSISTENT Modal chat worker...")
    chat_worker = Phi2ChatCls(
        base_model_repo="microsoft/phi-2",
        hf_token=HF_TOKEN
    )
    print(f"✔️  Persistent Modal chat worker spawned: {chat_worker}")
    yield
    print("👋 Terminating persistent chat worker...")
    chat_worker.shutdown.remote()
    print("✔️  Chat worker terminated.")

app.router.lifespan_context = lifespan

@app.post("/chat")
async def chat(request: Request) -> JSONResponse:
    data = await request.json()
    loraid = data.get("loraid")
    prompt = data.get("prompt")

    if not loraid or not prompt:
        return JSONResponse({"error": "Missing loraid or prompt"}, status_code=400)

    try:
        print("🚀 Sending prompt to Modal...")

        max_new_tokens, end_prompt, participants = get_dataset_analysis(loraid)

        response = chat_worker.chat_with_lora.remote(
            lora_repo=f"{HF_USERNAME}/{loraid}-model",
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            end_prompt=end_prompt,
            participants=participants
        )
        return {"response": response}
    except Exception as e:
        print("❌ ERROR GETTING RESPONSE")
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

# ------------------------------------------------- GENERATING VOICE ------------------------------------------------- #
@app.post("/generate-voice")
async def generate_voice(request: Request, background_tasks: BackgroundTasks):
    print("🧠 In the backend ... training voice ...")
    data = await request.json()

    lora_id = data.get("loraId")
    text = data.get("rawText")
    participants = data.get("participants")

    # Convert to JSONL string
    jsonl_str = text_to_axolotl_json(text)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(jsonl_str)
        temp_file.flush()
    
    # Analyze dataset
    try:
        analysis = analyze_dataset(temp_file_path, participants)
        save_dataset_analysis(lora_id, analysis)  # save into Supabase
    except Exception as e:
        print(f"⚠️ Failed to analyze dataset: {e}")
        analysis = None

    background_tasks.add_task(train_lora, lora_id, temp_file_path)
    background_tasks.add_task(delete_file_after_delay, temp_file_path, 10)

    return {
        "status": "processing",
        "message": "Dataset submitted. LoRA fine-tuning will run in the background.",
    }

async def delete_file_after_delay(file_path: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🧹 Temp file deleted: {file_path}")
    except Exception as e:
        print(f"⚠️ Error deleting temp file: {e}")

def clean_unicode(text: str) -> str:
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",     # en dash
        "—": "-",     # em dash
        "…": "...",   # ellipsis
        "•": "-",     # bullet
        " ": " ",     # narrow no-break space
        "\u00A0": " ",  # non-breaking space
    }

    # Replace known characters
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Normalize text to a consistent form
    text = unicodedata.normalize('NFKC', text)

    return text

def remove_all_unicode_except_ascii(text: str) -> str:
    """
    Keep standard ASCII letters, digits, and all common special characters.
    Removes emojis and other unwanted unicode characters.
    """
    allowed_chars = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        " ~!@#$%^&*()-=_+[]{};':\"\\|,.<>/?"
    )
    return "".join(c for c in text if c in allowed_chars)

def text_to_axolotl_json(raw_text: str) -> str:
    """
    Convert raw JSONL conversation text into Axolotl format.
    Returns a JSONL string where each line is a separate sample with a `messages` list.
    """
    conversation_jsonl = []

    for line in raw_text.strip().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            text = obj.get("text", "").strip()
            text = clean_unicode(text)
            text = remove_all_unicode_except_ascii(text)

            # Split into turns by 'User:' or 'Assistant:'
            pattern = r"(User|Assistant):\s*(.*?)(?=(User|Assistant):|$)"
            matches = re.findall(pattern, text, flags=re.DOTALL)

            messages = []
            for match in matches:
                role_label = match[0].lower()
                content = match[1].strip()
                role = "user" if role_label == "user" else "assistant"
                if content:
                    messages.append({"role": role, "content": content})

            if messages:
                # Each conversation block becomes one JSONL line
                conversation_jsonl.append(json.dumps({"messages": messages}, ensure_ascii=False))

        except json.JSONDecodeError:
            print(f"⚠️ Could not decode line: {line[:80]}...")

    # Join all conversation blocks with newline to produce valid JSONL
    return "\n".join(conversation_jsonl)

def save_dataset_analysis(lora_id: str, analysis: dict):
    try:
        supabase.table("loras").update({
            "dataset_analysis": analysis
        }).eq("id", lora_id).execute()
        print(f"✅ Saved dataset analysis for lora {lora_id}")
    except Exception as e:
        print(f"⚠️ Failed to save dataset analysis: {e}")

def get_dataset_analysis(loraid: str) -> tuple:
    # fetch dataset_analysis from Supabase
    resp = supabase.table("loras").select("dataset_analysis").eq("id", loraid).single().execute()
    dataset_analysis = resp.data.get("dataset_analysis") if resp.data else None

    max_new_tokens = 100  # default fallback
    end_prompt = None
    participants = {}

    if dataset_analysis:
        max_new_tokens = dataset_analysis.get("max_new_tokens", max_new_tokens)
        end_prompt = dataset_analysis.get("end_prompt")
        participants = dataset_analysis.get("participants", [])
    
    return max_new_tokens, end_prompt, participants
