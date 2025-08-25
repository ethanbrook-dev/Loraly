# dataset_analyzer.py

import json
import re
import numpy as np
from typing import List

def analyze_dataset(jsonl_path: str, participants: List[str]):
    """
    Analyze dataset JSONL (Axolotl format with messages[]).
    Returns dict with generation settings + a custom end_prompt string.
    Also returns the participants list for Supabase storage.
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
            "end_prompt": "(Answer naturally.)",
            "participants": participants or []
        }

    avg_len = np.mean(msg_lengths)

    # Heuristic: prefer 95th percentile * 1.2, fallback to avg if dataset is too small
    if len(msg_lengths) > 10:
        p95_len = np.percentile(msg_lengths, 95)
        max_new_tokens = int(min(512, max(32, p95_len * 1.2)))
    else:
        max_new_tokens = int(min(512, max(32, avg_len * 2)))

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
        "stats": {
            "avg_msg_len": avg_len,
            "emoji_density": emoji_count / max(1, len(all_msgs)),
            "slang_density": slang_count / max(1, len(all_msgs)),
        },
        "participants": participants or []
    }
