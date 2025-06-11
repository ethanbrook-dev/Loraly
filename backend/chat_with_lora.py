import modal
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

app = modal.App("mistral-lora-chat")

image = (
    modal.Image.debian_slim()
    .run_commands([
        "apt-get update",
        "apt-get install -y git build-essential cmake"
    ])
    .pip_install("torch", "transformers", "accelerate", "peft", "sentencepiece")
)


# ✅ This class will stay alive between requests (no reloads per prompt)
@app.cls(gpu="A100-80GB", image=image, timeout=900)
class MistralChat:
        
    def load(self, hf_token: str):
        print("🔄 Loading base model & tokenizer once per container...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            token=hf_token
        )
        self.base_model = AutoModelForCausalLM.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            torch_dtype=torch.float16,
            device_map="auto",
            token=hf_token
        ).half().to("cuda")
        self.loaded_loras = {}

    @modal.method()
    def chat_with_lora(self, hf_username: str, hf_token: str, lora_id: str, prompt: str) -> str:
        
        if not hasattr(self, "base_model") or not hasattr(self, "tokenizer"):
            self.load(hf_token)

        model_repo_id = f"{hf_username}/{lora_id}-model" # DO NOT CHANGE THIS -> the docker image will create this repo
        
        if lora_id not in self.loaded_loras:
            print(f"⚡ Loading LoRA: {lora_id} with modelID: {model_repo_id}")
            try:
                lora_model = PeftModel.from_pretrained(self.base_model, model_repo_id, token=hf_token)
            except Exception as e:
                raise RuntimeError(f"Failed to load LoRA model from {model_repo_id}: {e}")

            self.loaded_loras[lora_id] = lora_model
        else:
            lora_model = self.loaded_loras[lora_id]

        if not prompt.strip():
            return "⚠️ Empty prompt provided."

        print("🧠 Formatting prompt...")
        formatted = f"[INST] {prompt.strip()} [/INST]"

        print("🔢 Tokenizing...")
        inputs = self.tokenizer(formatted, return_tensors="pt").to(lora_model.device)

        print("🧪 Generating response...")
        with torch.no_grad():
            outputs = lora_model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        print("📝 Decoding output...")
        output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        reply = output_text.split("[/INST]")[-1].strip()
        print(f"✅ Reply ready. Reply is \"{reply}\"")

        return reply
