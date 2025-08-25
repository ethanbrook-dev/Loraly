# chat_with_lora.py

import modal
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch
import re
from huggingface_hub import login

# ANSI color codes for debug outputs
GREEN = "\033[92m"      # Success
YELLOW = "\033[93m"     # Info
RED = "\033[91m"        # Errors
CYAN = "\033[96m"       # Highlights for sizes
MAGENTA = "\033[95m"    # Warnings/mismatches
BLUE = "\033[94m"       # Misc debug
WHITE = "\033[97m"      # Additional info
RESET = "\033[0m"

app = modal.App("phi2-lora-chat")
model_volume = modal.Volume.from_name("hf-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim()
    .run_commands(["apt-get update", "apt-get install -y git build-essential cmake"])
    .pip_install("torch", "transformers", "accelerate", "peft", "sentencepiece")
)

@app.cls(gpu="A100-80GB", image=image, timeout=900, volumes={"/cache": model_volume})
class Phi2Chat:

    def load(self, model_repo: str, hf_token: str):
        print(f"{YELLOW}[INFO] Logging in to Hugging Face Hub...{RESET}")
        login(token=hf_token)
        print(f"{GREEN}[SUCCESS] Logged in successfully{RESET}")

        if getattr(self, "_model_loaded", False):
            print(f"{YELLOW}[INFO] Model already loaded, skipping...{RESET}")
            return

        # Load tokenizer
        print(f"{YELLOW}[INFO] Loading tokenizer from repo {model_repo}...{RESET}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_repo,
            use_fast=True,
            token=hf_token,
            cache_dir="/cache",
            trust_remote_code=False,
            force_download=True
        )
        print(f"{GREEN}[SUCCESS] Tokenizer loaded. Original vocab size: {len(self.tokenizer)}{RESET}")

        # Add missing special tokens
        special_tokens = {"bos_token": "<|im_start|>", "eos_token": "<|im_end|>", "pad_token": "<|im_end|>"}
        added = {}
        for k, v in special_tokens.items():
            if getattr(self.tokenizer, k) is None:
                self.tokenizer.add_special_tokens({k: v})
                added[k] = v
        if added:
            print(f"{GREEN}[INFO] Added missing special tokens: {added}. New vocab size: {len(self.tokenizer)}{RESET}")
        else:
            print(f"{GREEN}[INFO] All special tokens already present. No changes made.{RESET}")

        # Load base model WITHOUT resizing embeddings yet
        print(f"{YELLOW}[INFO] Loading base model: {model_repo}...{RESET}")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            model_repo,
            torch_dtype=torch.float16,
            device_map="auto",
            token=hf_token,
            cache_dir="/cache",
            trust_remote_code=False,
            force_download=True
        ).half().to("cuda")
        print(f"{GREEN}[SUCCESS] Base model loaded.{RESET}")
        print(f"{BLUE}[DEBUG] Base model embedding matrix shape: {self.base_model.get_input_embeddings().weight.shape}{RESET}")

        self.loaded_loras = {}
        self._model_loaded = True
        print(f"{GREEN}[INFO] Base model ready for LoRA loading.{RESET}")

    def get_lora_model(self, lora_repo: str, hf_token: str):
        if lora_repo in self.loaded_loras:
            print(f"{YELLOW}[INFO] LoRA {lora_repo} already loaded. Using cache.{RESET}")
            return self.loaded_loras[lora_repo]

        print(f"{YELLOW}[INFO] Loading LoRA from repo: {lora_repo}...{RESET}")
        try:
            lora_model = PeftModel.from_pretrained(
                self.base_model,
                lora_repo,
                token=hf_token
            )
            print(f"{GREEN}[SUCCESS] LoRA loaded successfully!{RESET}")
        except Exception as e:
            print(f"{RED}[ERROR] Failed to load LoRA: {e}{RESET}")
            raise RuntimeError(f"Failed to load LoRA {lora_repo}: {e}")

        # Debug info about embeddings
        base_emb = self.base_model.get_input_embeddings().weight.shape
        lora_emb = lora_model.get_input_embeddings().weight.shape
        print(f"{CYAN}[INFO] Base model embedding shape: {base_emb}{RESET}")
        print(f"{CYAN}[INFO] LoRA embedding shape: {lora_emb}{RESET}")

        # Resize tokenizer / embeddings AFTER LoRA if needed
        tokenizer_size = len(self.tokenizer)
        if tokenizer_size > lora_emb[0]:
            print(f"{MAGENTA}[WARN] Tokenizer vocab ({tokenizer_size}) > LoRA vocab ({lora_emb[0]}). Resizing embeddings...{RESET}")
            lora_model.resize_token_embeddings(tokenizer_size)
            with torch.no_grad():
                lora_model.get_input_embeddings().weight[:lora_emb[0], :] = self.base_model.get_input_embeddings().weight
            print(f"{GREEN}[SUCCESS] Embeddings resized and overlapping weights copied.{RESET}")

        print(f"{GREEN}[INFO] LoRA model ready for generation.{RESET}")
        self.loaded_loras[lora_repo] = lora_model
        return lora_model

    def format_chatml_user_prompt(self, user_prompt: str, end_prompt: str = None) -> str:
        """
        Format the user message for ChatML, optionally appending a dynamic end_prompt.
        """
        end_prompt_text = end_prompt or "(Answer naturally in the same style, and also ask a follow-up question to keep the conversation going.)"
        
        return (
            "<|im_start|>user\n"
            f"{user_prompt}<|im_end|>\n"
            "<|im_start|>assistant\n"
            f"{end_prompt_text}\n"
        )
    
    @modal.method()
    def chat_with_lora(self, base_model_repo: str, lora_repo: str, hf_token: str, prompt: str, max_new_tokens: int, end_prompt: str = None) -> str:
        print(f"{YELLOW}[INFO] chat_with_lora called{RESET}")

        self.load(base_model_repo, hf_token)
        lora_model = self.get_lora_model(lora_repo, hf_token)

        if not prompt.strip():
            print(f"{MAGENTA}[WARN] Empty prompt received{RESET}")
            return "[INFO] Empty prompt provided."

        print(f"{YELLOW}[INFO] Tokenizing prompt...{RESET}")
        
        fomatted_prompt = self.format_chatml_user_prompt(prompt, end_prompt)
        inputs = self.tokenizer(fomatted_prompt.strip(), return_tensors="pt").to(lora_model.device)

        print(f"{YELLOW}[INFO] Generating response...{RESET}")
        with torch.no_grad():
            outputs = lora_model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.4,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id  # use tokenizer-defined EOS consistently
            )

        # Slice off the input so only new tokens remain
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]

        reply = self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        # Clean junk tokens like <@a>
        reply = re.sub(r"<[@:].*?>", "", reply)
        
        print(f"{GREEN}[SUCCESS] Reply ready: {reply}{RESET}")
        return reply
