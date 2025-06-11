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
@app.cls(gpu="A100", image=image, timeout=900)
class MistralChat:
    def __enter__(self):
        print("🔄 Loading base model & tokenizer once per container...")
        self.tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3")
        base_model = AutoModelForCausalLM.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.base_model = base_model
        self.loaded_loras = {}

    @modal.method()
    def chat_with_lora(self, lora_id: str, prompt: str) -> str:
        
        model_repo_id = f"{UUUUUUUUUUU}/{lora_id}-model" # DO NOT CHANGE THIS -> the docker image will create this repo
        
        if lora_id not in self.loaded_loras:
            print(f"⚡ Loading LoRA: {lora_id} with modelID: {model_repo_id}")
            lora_model = PeftModel.from_pretrained(self.base_model, model_repo_id, token=UUUUUUUUUUUUU)
            self.loaded_loras[lora_id] = lora_model
        else:
            lora_model = self.loaded_loras[lora_id]

        formatted = f"[INST] {prompt.strip()} [/INST]"
        inputs = self.tokenizer(formatted, return_tensors="pt").to(lora_model.device)

        with torch.no_grad():
            outputs = lora_model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        output_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        reply = output_text.split("[/INST]")[-1].strip()
        return reply
