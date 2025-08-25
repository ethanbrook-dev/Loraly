# dataset_analyzer.py

import json
import re
import numpy as np
from collections import Counter

def analyze_dataset(jsonl_path: str):
    """
    Analyze dataset JSONL (Axolotl format with messages[]).
    Returns dict with generation settings + a custom end_prompt string.
    """

    msg_lengths = []
    all_msgs = []
    emoji_count = 0
    slang_count = 0

    # very rough slang detection (can extend with a dictionary)
    slang_words = {"lol", "omg", "idk", "lmao", "brb", "btw", "smth", "nah", "tho"}

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            for msg in obj.get("messages", []):
                content = msg["content"].strip()
                if not content:
                    continue

                all_msgs.append(content)
                msg_lengths.append(len(content.split()))

                # detect emojis (unicode ranges)
                emoji_count += sum(
                    1 for ch in content if (ord(ch) > 127 and not ch.isalnum())
                )

                # detect slang
                tokens = re.findall(r"\w+", content.lower())
                slang_count += sum(1 for t in tokens if t in slang_words)

    if not all_msgs:
        return {
            "max_new_tokens": 128,
            "end_prompt": "(Answer naturally.)"
        }

    avg_len = np.mean(msg_lengths)

    # Heuristic: set max_new_tokens to average length, bounded between 64 and 512
    max_new_tokens = int(min(512, max(64, avg_len)))

    # Build dynamic end prompt
    style_bits = []

    if avg_len < 8:
        style_bits.append("Keep replies short and casual")
    elif avg_len > 20:
        style_bits.append("Give longer, detailed replies")
    else:
        style_bits.append("Match the same tone and length")

    if emoji_count / max(1, len(all_msgs)) > 0.2:
        style_bits.append("Use emojis naturally")
    if slang_count / max(1, len(all_msgs)) > 0.05:
        style_bits.append("Include slang if it fits the context")

    # Always encourage continuation
    style_bits.append("Ask a follow-up question to keep the chat going")

    end_prompt = "(" + ", and ".join(style_bits) + ".)"

    return {
        "max_new_tokens": max_new_tokens,
        "end_prompt": end_prompt,
        "stats": { # not currently used. Optional statistics for debugging and analysis
            "avg_msg_len": avg_len,
            "emoji_density": emoji_count / max(1, len(all_msgs)),
            "slang_density": slang_count / max(1, len(all_msgs)),
        },
    }
