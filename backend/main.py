from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# For training:
import json, tempfile, re, os, asyncio
from backend.upload_ds_and_train_lora import upload_ds_and_train_lora

# For chatting:
from contextlib import asynccontextmanager
import modal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        response = await chat_worker.chat_with_lora.remote(loraid, prompt)
        print(f"✅ Response: {response}")
        return {"response": response}
    except Exception as e:
        print("❌ ERROR GETTING RESPONSE")
        return JSONResponse({"error": str(e)}, status_code=500)

# ------------------------------------------------- GENERATING VOICE API ------------------------------------------------- #
@app.post("/generate-voice")
async def generate_voice(request: Request, background_tasks: BackgroundTasks):
    print("🧠 In the backend ... training voice ...")
    data = await request.json()

    lora_id = data.get("loraId")
    text = data.get("rawText")

    jsonl_str = text_to_jsonl_string(text)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl") as temp_file:
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

def text_to_jsonl_string(raw_text: str) -> str:
    cleaned_text = (
        raw_text.replace("’", "'")
                .replace("‘", "'")
                .replace("“", '"')
                .replace("”", '"')
    )
    sentences = re.findall(r'[^.?!]+[.?!]', cleaned_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lines = [json.dumps({"text": sentence}, ensure_ascii=False) for sentence in sentences]
    return "\n".join(lines)

