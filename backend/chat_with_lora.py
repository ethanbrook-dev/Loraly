# chat_with_lora.py

import modal
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch
import json
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

    # Define class parameters
    base_model_repo: str = modal.parameter()
    hf_token: str = modal.parameter()

    @modal.enter()
    def setup(self):
        """
        Lifecycle hook. Runs ONCE when the container starts.
        Initializes empty state. The base model will be loaded on first request.
        """
        print(f"{GREEN}[LIFECYCLE] Container spawned. Initializing empty state.{RESET}")
        self.loaded_loras = {}
        self._base_model_loaded = False
        self.tokenizer = None
        self.base_model = None

    @modal.method()
    def shutdown(self):
        """
        Manually clear state & free memory.
        This gives a callable way to 'terminate' early.
        """
        self.loaded_loras.clear()
        self.base_model = None
        self.tokenizer = None
        print("[LIFECYCLE] Manual shutdown triggered")
        return "[INFO] Chat worker shut down manually."
    
    def _ensure_base_model_loaded(self, model_repo: str, hf_token: str):
        """
        Internal method to load the base model and tokenizer.
        Only runs the expensive loading logic once per container lifetime.
        """
        if self._base_model_loaded:
            # Base model is already loaded, nothing to do.
            print(f"{YELLOW}[INFO] Base model already loaded. Skipping.{RESET}")
            return

        print(f"{YELLOW}[INFO] Logging in to Hugging Face Hub...{RESET}")
        login(token=hf_token)
        self.hf_token = hf_token
        print(f"{GREEN}[SUCCESS] Logged in successfully{RESET}")

        # Load tokenizer
        print(f"{YELLOW}[INFO] Loading tokenizer from repo {model_repo}...{RESET}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_repo,
            use_fast=True,
            token=hf_token,
            cache_dir="/cache",
            trust_remote_code=False,
            force_download=False
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

        self._base_model_loaded = True
        print(f"{GREEN}[INFO] Base model ready for LoRA loading.{RESET}")

    def get_lora_model(self, lora_repo: str):
        """
        Gets a LoRA model from the cache, loading it if necessary.
        Assumes the base model is already loaded.
        """
        if lora_repo in self.loaded_loras:
            print(f"{YELLOW}[INFO] LoRA {lora_repo} already loaded. Using cache.{RESET}")
            return self.loaded_loras[lora_repo]

        print(f"{YELLOW}[INFO] Loading LoRA from repo: {lora_repo}...{RESET}")
        try:
            lora_model = PeftModel.from_pretrained(
                self.base_model,
                lora_repo,
                token=self.hf_token
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

        # Resize tokenizer / embeddings if needed
        tokenizer_size = len(self.tokenizer)
        if tokenizer_size != lora_emb[0]:
            print(f"{MAGENTA}[WARN] Resizing embeddings to match tokenizer ({tokenizer_size}){RESET}")
            lora_model.resize_token_embeddings(tokenizer_size)
            with torch.no_grad():
                lora_model.get_input_embeddings().weight[:lora_emb[0], :] = self.base_model.get_input_embeddings().weight
            print(f"{GREEN}[SUCCESS] Embeddings resized and overlapping weights copied.{RESET}")

        print(f"{GREEN}[INFO] LoRA model ready for generation.{RESET}")
        self.loaded_loras[lora_repo] = lora_model
        return lora_model

    def format_chatml_conversation(
        self,
        history: list,
        end_prompt: str = None,
        participants: dict = None,
        max_tokens: int = 1800
    ) -> str:
        """
        Build a ChatML-style conversation string from chat history,
        keeping only the most recent turns that fit within max_tokens.
        
        Args:
            history: [{ "sender": "You", "message": "..."}, {...}]
            end_prompt: Optional system instruction (e.g. "Stay concise.")
            participants: {"user": "You", "assistant": "Maddy"} 
                        maps roles to display names
            max_tokens: rough token budget for history
        
        Returns:
            str: ChatML-formatted prompt ready for tokenization.
        """
        if participants is None:
            participants = {"user": "You", "assistant": "Assistant"}
        
        lines = []

        # Optional: add a system prompt at the very start
        if end_prompt:
            lines.append(f"<|im_start|>system\n{end_prompt}<|im_end|>")

        total_tokens = 0

        # Walk backwards through history (most recent first)
        for turn in reversed(history):
            # Map sender -> ChatML role
            if turn["sender"] == participants.get("user", "You"):
                role = "user"
            elif turn["sender"] == participants.get("assistant", "Assistant"):
                role = "assistant"
            else:
                role = "user"  # default fallback

            entry = f"<|im_start|>{role}\n{turn['message']}<|im_end|>"

            # Estimate tokens
            tokens = len(self.tokenizer.encode(entry))
            if total_tokens + tokens > max_tokens:
                break
            total_tokens += tokens

            # Prepend so order is correct
            lines.insert(0, entry)

        # Always end with assistant’s "turn to speak"
        lines.append("<|im_start|>assistant\n")
        return "\n".join(lines)

    
    @modal.method()
    def chat_with_lora(
        self,
        lora_repo: str,
        chat_history: str, # json string of [{sender, message}, ...]
        max_new_tokens: int,
        end_prompt: str = None,
        participants: dict = None
    ) -> str:
        print(f"{YELLOW}[INFO] chat_with_lora called{RESET}")
        
        # Deserialize JSON string into a Python list
        try:
            chat_history = json.loads(chat_history)
        except Exception as e:
            print(f"{RED}[ERROR] Failed to parse chat_history JSON: {e}{RESET}")
            raise ValueError("Invalid chat_history JSON provided") from e

        # This ensures the base model is loaded (only happens on first call)
        self._ensure_base_model_loaded(self.base_model_repo, self.hf_token)
        # This uses the persistent cache for LoRAs
        lora_model = self.get_lora_model(lora_repo)

        if not chat_history or not isinstance(chat_history, list):
            print(f"{MAGENTA}[WARN] Empty or invalid chat_history received{RESET}")
            return "[INFO] No conversation history provided."

        # Allocate 80% for history, 20% for new response
        model_max = getattr(lora_model.config, "max_position_embeddings", 2048)
        history_budget = int(model_max * 0.8)

        print(f"{YELLOW}[INFO] Building ChatML conversation prompt...{RESET}")
        formatted_prompt = self.format_chatml_conversation(
            chat_history, 
            end_prompt, 
            participants, 
            max_tokens=history_budget
        )

        inputs = self.tokenizer(formatted_prompt.strip(), return_tensors="pt").to(lora_model.device)

        print(f"{YELLOW}[INFO] Generating response...{RESET}")
        with torch.no_grad():
            outputs = lora_model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.4,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.3,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id  # uses the tokenizer-defined EOS consistently
            )

        # Slice off the input so only new tokens remain
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]

        reply = self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        reply = self.filter_output(reply)
        
        print(f"{GREEN}[SUCCESS] Reply ready: {reply}{RESET}")
        return reply
    
    def filter_output(self, text: str) -> str:
        
        # Clean junk tokens like <@a>
        text = re.sub(r"<[@:].*?>", "", text)
        
        # Remove full or partial ChatML tokens
        text = re.sub(r"<\|im_(start|end)\|>", "", text)
        
        # Clean extra whitespace/newlines
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return text.strip()