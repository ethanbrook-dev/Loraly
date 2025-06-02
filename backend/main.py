from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import json, tempfile, re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # "http://localhost:3000"
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

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(text_to_jsonl_string(text))
        temp_file.flush()
        
    #################################################################################

    return {
        "status": "processing",
        "message": "Dataset submitted. LoRA fine-tuning will run in the background.",
    }

def text_to_jsonl_string(raw_text: str) -> str:
    # This regex splits at . or ? or ! while keeping the punctuation
    sentences = re.findall(r'[^.?!]+[.?!]', raw_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    lines = [json.dumps({"text": sentence}, ensure_ascii=False) for sentence in sentences]
    return "\n".join(lines)
