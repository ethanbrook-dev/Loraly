# main.py - the entrypoint for the backend 

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# For training:
import json, tempfile, re, unicodedata
import os, asyncio
from backend.upload_ds_and_train_lora import upload_ds_and_train_lora

# For chatting:
from contextlib import asynccontextmanager
import modal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev - tighter restrictions getFrontendUrl()
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(dotenv_path=env_path)

# ------------------------------------------------- CHATTING API ------------------------------------------------- #
# 🔁 Correct way to hydrate class from deployed Modal App
MistralChatCls = modal.Cls.from_name("mistral-lora-chat", "MistralChat")

chat_worker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global chat_worker
    print("🔌 Connecting to Modal chat worker...")
    chat_worker = MistralChatCls()  # This is the worker instance (proxy)
    print(f"✔️  Connected to Modal chat worker: {chat_worker}")
    yield
    print("👋 Shutting down chat worker...")

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
        response = chat_worker.chat_with_lora.remote(
            hf_username=os.getenv("HF_USERNAME"),
            hf_token=os.getenv("HF_TOKEN"), 
            lora_id=loraid, 
            prompt=prompt
        )
        response = response.replace(prompt, "").strip()
        return {"response": response}
    except Exception as e:
        import traceback
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

    jsonl_str = text_to_axolotl_json(text)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl", encoding="utf-8") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(jsonl_str)
        temp_file.flush()

    background_tasks.add_task(upload_ds_and_train_lora, lora_id, temp_file_path)
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
    # Remove emojis and all other non-ASCII characters
    return text.encode("ascii", errors="ignore").decode()
    """Returns a list of all non-ASCII characters in the string"""
    return [char for char in set(text) if ord(char) > 127]

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
