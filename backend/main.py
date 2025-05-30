from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, json, tempfile

# Load environment variables
load_dotenv('.env.local')
hf_token = os.getenv("NEXT_PUBLIC_HF_TOKEN")

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

    print("\n=== LoRA Training Request Received ===")
    print("LoRA ID:", lora_id)
    print("Email:", email)
    print("Raw Text:\n", text[:300], "...\n")  # print first 300 chars

    # Step 1: Convert to JSONL string
    jsonl_str = text_to_jsonl_string(text)
    print("\n[DEBUG] First few lines of JSONL:")
    print(jsonl_str[:300], "...\n")  # print first 300 chars of JSONL
    if not jsonl_str:
        return {"status": "error", "message": "No valid text provided for LoRA training."}
    
    # Step 2: Create a temporary dataset file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".jsonl") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(jsonl_str)
        temp_file.flush()
        print(f"\n✅ Temp dataset file created at: {temp_file_path}")

    # 🧠🛠️📤📥🚀
    """
    ⏳ NEXT STEP: Upload this dataset manually to Hugging Face as a private dataset
    👉 Go to: https://huggingface.co/datasets
    👉 Click "New Dataset" (make it private)
    👉 Upload this JSONL file: {temp_file_path}
    
    ✅ Once uploaded, go to RunPod Fine Tuning tab and:
       - Paste in your HF model ID (e.g., mistralai/Mistral-7B-Instruct-v0.3)
       - Paste your dataset repo ID (e.g., your-user/my-private-dataset)
       - Trigger the fine-tuning run!
    
    ⚠️ After successful training, don’t forget to delete this temp file!
    """

    # Step 3: Cleanup temp file (we assume lora training is done)
    try:
        os.remove(temp_file_path)
        print(f"🧹 Temp file deleted: {temp_file_path}")
    except Exception as e:
        print(f"⚠️ Error deleting temp file: {e}")
    
    #Remember to send email to user
    print("\n✅ LoRA training request processed successfully!")
    print("📧 Sending email to:", email)
    
    return {
        "status": "ready",
        "message": "Dataset prepared. Please upload to HF and start fine-tuning manually.",
    }

def text_to_jsonl_string(raw_text: str) -> str:
    sentences = raw_text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    lines = [json.dumps({"text": sentence + "."}, ensure_ascii=False) for sentence in sentences]
    return "\n".join(lines)