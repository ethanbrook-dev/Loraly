from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os, json, tempfile, re
from backend.upload_ds_and_train_lora import upload_ds_and_train_lora

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

    # Step 1: Convert to JSONL string
    jsonl_str = text_to_jsonl_string(text)
    
    # Step 2: Create a temporary dataset file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(jsonl_str)
        temp_file.flush()

    upload_ds_and_train_lora(lora_id, temp_file_path)

    # Step 3: Cleanup temp file (we assume lora training is done)
    try:
        os.remove(temp_file_path)
    except Exception as e:
        print(f"⚠️ Error deleting temp file: {e}")
    
    # Delete ds from hf
    
    # Remember to send email to user
    # print("\n✅ LoRA training request processed successfully!")
    # print("📧 Sending email to:", email)
    
    return {
        "status": "ready",
        "message": "Dataset prepared. Please upload to HF and start fine-tuning manually.",
    }

def text_to_jsonl_string(raw_text: str) -> str:
    # This regex splits at . or ? or ! while keeping the punctuation
    sentences = re.findall(r'[^.?!]+[.?!]', raw_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lines = [json.dumps({"text": sentence}, ensure_ascii=False) for sentence in sentences]
    return "\n".join(lines)
