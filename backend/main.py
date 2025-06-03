from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import json, tempfile, re, os, asyncio
from backend.upload_ds_and_train_lora import upload_ds_and_train_lora

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "http://localhost:3000"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-voice")
async def generate_voice(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    lora_id = data.get("loraId")
    text = data.get("rawText")
    email = data.get("userEmail")

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
            print(f"Temp file deleted: {file_path}")
    except Exception as e:
        print(f"Error deleting temp file: {e}")

def text_to_jsonl_string(raw_text: str) -> str:
    # This regex splits at . or ? or ! while keeping the punctuation
    sentences = re.findall(r'[^.?!]+[.?!]', raw_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lines = [json.dumps({"text": sentence}, ensure_ascii=False) for sentence in sentences]
    return "\n".join(lines)
