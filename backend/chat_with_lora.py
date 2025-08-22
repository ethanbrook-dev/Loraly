# chat_with_lora.py is a script pushed to Modal 

import modal
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

app = modal.App("mistral-lora-chat")

model_volume = modal.Volume.from_name("hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim()
    .run_commands([
        "apt-get update",
        "apt-get install -y git build-essential cmake"
    ])
    .pip_install("torch", "transformers", "accelerate", "peft", "sentencepiece")
)

# ✅ This class will stay alive between requests (no reloads per prompt)
@app.cls(gpu="A100-80GB", image=image, timeout=900, volumes={"/cache": model_volume})
class MistralChat:

    def load(self, hf_token: str):
        print("🔄 Loading base model & tokenizer once per container...")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            token=hf_token,
            cache_dir="/cache"
        )
        print(f"📌 Tokenizer loaded. Vocab size: {len(self.tokenizer)}")

        # Add missing special tokens
        special_tokens = {"eos_token": "<|im_end|>", "bos_token": "<|im_start|>"}
        num_added = self.tokenizer.add_special_tokens(special_tokens)
        print(f"🔑 Added {num_added} special tokens")

        # Load base model
        print("🛠 Loading base model...")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.3",
            torch_dtype=torch.float16,
            device_map="auto",
            token=hf_token,
            cache_dir="/cache"
        ).half().to("cuda")
        print(f"✅ Base model loaded. Embedding size: {self.base_model.get_input_embeddings().weight.size(0)}")

        # Ensure embeddings match tokenizer
        print("📏 Resizing base model embeddings to match tokenizer...")
        self.base_model.resize_token_embeddings(len(self.tokenizer))
        print(f"✅ Embeddings resized: {self.base_model.get_input_embeddings().weight.size(0)}")

        self.loaded_loras = {}

    def get_lora_model(self, hf_username: str, lora_id: str, hf_token: str):
        print(f"🚀 Preparing LoRA model: {lora_id}")
        model_repo_id = f"{hf_username}/{lora_id}-model"

        if lora_id in self.loaded_loras:
            print(f"⚡ LoRA model {lora_id} already loaded, returning cached instance")
            return self.loaded_loras[lora_id]

        # Resize base embeddings just in case
        vocab_size = len(self.tokenizer)
        current_size = self.base_model.get_input_embeddings().weight.size(0)
        print(f"📌 Base model vocab: {current_size}, tokenizer vocab: {vocab_size}")
        if current_size != vocab_size:
            print(f"📏 Resizing embeddings before loading LoRA: {current_size} -> {vocab_size}")
            self.base_model.resize_token_embeddings(vocab_size)

        # Load LoRA
        try:
            print(f"⚡ Loading LoRA from {model_repo_id}...")
            lora_model = PeftModel.from_pretrained(
                self.base_model,
                model_repo_id,
                token=hf_token
            )
            print("✅ LoRA loaded successfully")

            # Trim last 2 rows in embedding weights if mismatch
            lora_vocab_size = lora_model.get_input_embeddings().weight.size(0)
            if lora_vocab_size > vocab_size:
                print(f"✂️ Trimming LoRA embeddings: {lora_vocab_size} -> {vocab_size}")
                with torch.no_grad():
                    for name, param in lora_model.named_parameters():
                        if "embed_tokens" in name or "lm_head" in name:
                            param.data = param.data[:vocab_size, :]
                print("✅ LoRA embeddings trimmed successfully")

        except Exception as e:
            print("❌ Failed to load LoRA")
            raise RuntimeError(f"Failed to load LoRA model from {model_repo_id}: {e}")

        self.loaded_loras[lora_id] = lora_model
        return lora_model

    @modal.method()
    def chat_with_lora(self, hf_username: str, hf_token: str, lora_id: str, prompt: str) -> str:
        print("💬 chat_with_lora called")
        if not hasattr(self, "base_model") or not hasattr(self, "tokenizer"):
            print("⚡ Base model or tokenizer not loaded, calling load()")
            self.load(hf_token)

        lora_model = self.get_lora_model(hf_username, lora_id, hf_token)

        if not prompt.strip():
            print("⚠️ Empty prompt received")
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
