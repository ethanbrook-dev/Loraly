# chat_with_lora.py

import modal
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

app = modal.App("mistral-lora-chat")

# Persistent HF cache volume
model_volume = modal.Volume.from_name("hf-cache", create_if_missing=True)

# Modal image with dependencies
image = (
    modal.Image.debian_slim()
    .run_commands(["apt-get update", "apt-get install -y git build-essential cmake"])
    .pip_install("torch", "transformers", "accelerate", "peft", "sentencepiece")
)

@app.cls(gpu="A100-80GB", image=image, timeout=900, volumes={"/cache": model_volume})
class MistralChat:
    def load(self, hf_token: str):
        """Load tokenizer & base model once, resize embeddings, and cache LoRAs"""
        
        if getattr(self, "_model_loaded", False):
            return
        print("[DEBUG] Loading tokenizer and base model...")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            token=hf_token,
            cache_dir="/cache"
        )
        print(f"[DEBUG] Tokenizer loaded. Original vocab size: {len(self.tokenizer)}")

        # Add special tokens
        special_tokens = {"bos_token": "<|im_start|>", "eos_token": "<|im_end|>"}
        num_added = self.tokenizer.add_special_tokens(special_tokens)
        print(f"[DEBUG] Added {num_added} special tokens. New vocab size: {len(self.tokenizer)}")

        # Base model
        self.base_model = AutoModelForCausalLM.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            torch_dtype=torch.float16,
            device_map="auto",
            token=hf_token,
            cache_dir="/cache"
        ).half().to("cuda")

        # Resize embeddings to match tokenizer
        self.base_model.resize_token_embeddings(len(self.tokenizer))
        print(f"[DEBUG] Base model loaded. Embedding size: {self.base_model.get_input_embeddings().weight.size(0)}")

        self.loaded_loras = {}
        self._model_loaded = True

    def get_lora_model(self, hf_username: str, lora_id: str, hf_token: str):
        """Load LoRA on top of base model, cache for reuse"""
        if lora_id in self.loaded_loras:
            print(f"[DEBUG] LoRA {lora_id} already loaded, using cache")
            return self.loaded_loras[lora_id]

        model_repo_id = f"{hf_username}/{lora_id}-model"
        print(f"[DEBUG] Loading LoRA {lora_id} from {model_repo_id}...")

        try:
            lora_model = PeftModel.from_pretrained(self.base_model, model_repo_id, token=hf_token)
            print("[DEBUG] LoRA loaded successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to load LoRA {lora_id}: {e}")

        # Ensure embeddings align
        if lora_model.get_input_embeddings().weight.size(0) != len(self.tokenizer):
            lora_model.resize_token_embeddings(len(self.tokenizer))
            print(f"[DEBUG] Resized LoRA embeddings to {len(self.tokenizer)}")

        self.loaded_loras[lora_id] = lora_model
        return lora_model

    @modal.method()
    def chat_with_lora(self, hf_username: str, hf_token: str, lora_id: str, prompt: str) -> str:
        """Generate a response with base + LoRA model"""
        print("[DEBUG] chat_with_lora called")

        # Ensure model & tokenizer are loaded once
        self.load(hf_token)

        # Load or get cached LoRA
        lora_model = self.get_lora_model(hf_username, lora_id, hf_token)

        if not prompt.strip():
            print("[DEBUG] Empty prompt received")
            return "[INFO] Empty prompt provided."

        # Tokenize plain-text prompt
        inputs = self.tokenizer(prompt.strip(), return_tensors="pt").to(lora_model.device)

        # Generate response
        print("[DEBUG] Generating response...")
        with torch.no_grad():
            outputs = lora_model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        reply = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        print(f"[INFO] Reply ready: {reply}")

        return reply
