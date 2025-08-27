import json
import random
import re
import os
import time
from collections import Counter, defaultdict

from .slang_terms import get_all_slang_terms


def augment_dataset(jsonl_str: str, target_words: int = 200_000) -> str:
    """
    Augments a JSONL chat dataset into a larger one while preserving style.

    Args:
        jsonl_str (str): Input JSONL string, where each line is {"messages": [{"role":..., "content":...}, ...]}.
        target_words (int, optional): Target total word count after augmentation. Defaults to 200k.

    Returns:
        str: Augmented JSONL string with expanded dataset.
    """

    # ----------------------
    # Load original dataset
    # ----------------------
    conversations = [json.loads(line) for line in jsonl_str.strip().split("\n") if line.strip()]
    
    # Count total words in dataset
    def count_words(text):
        return len(text.split())

    original_word_count = sum(
        count_words(msg["content"]) for conv in conversations for msg in conv["messages"]
    )

    # ----------------------
    # Build style profiles
    # ----------------------
    style_profiles = defaultdict(lambda: {
        "variants": defaultdict(int),
        "emoji_freq": Counter(),
        "punctuation_freq": Counter(),
        "message_lengths": [],
    })

    slang_candidates = set(get_all_slang_terms(lowercase=True))

    for conv in conversations:
        for msg in conv["messages"]:
            role = msg["role"]
            text = msg["content"]

            # Record message length
            style_profiles[role]["message_lengths"].append(len(text.split()))

            # Record punctuation habits
            if "!!" in text:
                style_profiles[role]["punctuation_freq"]["!!"] += 1
            if "??" in text:
                style_profiles[role]["punctuation_freq"]["??"] += 1

            # Record emojis
            emojis = re.findall(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+", text)
            for e in emojis:
                style_profiles[role]["emoji_freq"][e] += 1

            # Record variants (slang & greetings)
            for word in text.lower().split():
                style_profiles[role]["variants"][word] += 1

    # Filter valid variants (slang must appear >= 5 times)
    for role, profile in style_profiles.items():
        profile["variants"] = {
            word: freq
            for word, freq in profile["variants"].items()
            if word not in slang_candidates or freq >= 5
        }

    # ----------------------
    # Augmentation functions
    # ----------------------

    def synonym_replace(text, role):
        """Replace words only with existing variants from style profile, avoiding consecutive repeats."""
        words = text.split()
        new_words = []
        prev_word = None

        for w in words:
            lw = w.lower()
            # Only try replacement if word exists in variants and randomly triggered
            if lw in style_profiles[role]["variants"] and random.random() < 0.2:
                # Pick only frequent variants (freq >= 5)
                candidates = [v for v, freq in style_profiles[role]["variants"].items() if freq >= 5]
                if candidates:
                    choice = random.choice(candidates)
                    # Avoid consecutive duplicate
                    while choice == prev_word and len(candidates) > 1:
                        choice = random.choice(candidates)
                    new_words.append(choice)
                    prev_word = choice
                else:
                    # No valid candidates: keep original word
                    new_words.append(w)
                    prev_word = w
            else:
                new_words.append(w)
                prev_word = w

        return " ".join(new_words)

    def remix_messages(messages):
        """Split or merge participant messages, avoiding consecutive duplicate words across merges and across roles."""
        new_msgs = []
        prev_msg = None

        for msg in messages:
            role, text = msg["role"], msg["content"]
            words = [w for w in text.split() if w]

            # Split on commas sometimes
            if "," in text and random.random() < 0.3:
                parts = [p.strip() for p in text.split(",") if p.strip()]
                for p in parts:
                    part_words = p.split()
                    # Avoid duplicates with previous message end (same role only)
                    if prev_msg and prev_msg["role"] == role and part_words and prev_msg_words[-1].lower() == part_words[0].lower():
                        part_words = part_words[1:]
                    new_msgs.append({"role": role, "content": " ".join(part_words)})
                    prev_msg = new_msgs[-1]
                    prev_msg_words = part_words
            # Merge with previous message sometimes, only if same role
            elif random.random() < 0.2 and prev_msg and prev_msg["role"] == role:
                prev_words = prev_msg["content"].split()
                # Remove duplicate at boundary
                if prev_words and words and prev_words[-1].lower() == words[0].lower():
                    words = words[1:]
                merged = " ".join(prev_words + words)
                new_msgs[-1] = {"role": role, "content": merged}
                prev_msg = new_msgs[-1]
                prev_msg_words = merged.split()
            else:
                new_msgs.append(msg)
                prev_msg = msg
                prev_msg_words = words

        return new_msgs

    def inject_noise(text, role):
        """Optional typos, abbreviations, emojis (only if already exist)."""
        if random.random() < 0.1:
            text = text.replace("gonna", "gon") if "gonna" in text else text
        if random.random() < 0.1 and style_profiles[role]["emoji_freq"]:
            text += random.choice(list(style_profiles[role]["emoji_freq"].keys()))
        return text

    # ----------------------
    # Augmentation loop
    # ----------------------

    avg_conv_words = original_word_count / len(conversations)
    needed_convs = (target_words - original_word_count) / avg_conv_words
    max_retries = int(needed_convs * 2)  # safety margin

    augmented = conversations[:]
    total_words = original_word_count
    retries = 0

    while total_words < target_words and retries < max_retries:
        base_conv = random.choice(conversations)
        new_conv = {"messages": []}

        for msg in base_conv["messages"]:
            role, text = msg["role"], msg["content"]

            # Step 1: synonym replacement
            aug_text = synonym_replace(text, role)

            # Step 2: optional noise injection
            aug_text = inject_noise(aug_text, role)

            new_conv["messages"].append({"role": role, "content": aug_text})

        # Step 3: remix message blocks
        new_conv["messages"] = remix_messages(new_conv["messages"])

        augmented.append(new_conv)
        total_words += sum(count_words(m["content"]) for m in new_conv["messages"])
        retries += 1

    # ----------------------
    # Export JSONL
    # ----------------------
    out_lines = [json.dumps(conv, ensure_ascii=False) for conv in augmented]

    # Final stats
    status_emoji = "✅" if total_words >= target_words else "❌"
    print(f"\nFinal word count: {total_words} / {target_words} {status_emoji}")

    return "\n".join(out_lines)

def main():
    # Example usage
    sample_jsonl = """
    {"messages": [{"role": "user", "content": "hey yo how are you?"}, {"role": "assistant", "content": "I'm good, how about you?"}]}
    {"messages": [{"role": "user", "content": "ayy whassup"}, {"role": "assistant", "content": "Not much, just chilling"}]}
    {"messages": [{"role": "user", "content": "hey what's up with your day?"}, {"role": "assistant", "content": "Pretty good, been busy with work"}]}
    {"messages": [{"role": "user", "content": "yo yo let's grab lunch soon"}, {"role": "assistant", "content": "Sure! When are you free?"}]}
    {"messages": [{"role": "user", "content": "gonna head to the gym later"}, {"role": "assistant", "content": "Nice, get those gains 💪"}]}
    {"messages": [{"role": "user", "content": "did you watch the game last night?"}, {"role": "assistant", "content": "Yeah! That last goal was insane 😲"}]}
    {"messages": [{"role": "user", "content": "haha that's wild"}, {"role": "assistant", "content": "Totally, can't believe it happened"}]}
    {"messages": [{"role": "user", "content": "you free this weekend?"}, {"role": "assistant", "content": "Yes, let's plan something fun"}]}
    {"messages": [{"role": "user", "content": "omg I can't wait 😆"}, {"role": "assistant", "content": "Me neither, gonna be great"}]}
    """
    
    print("Running dataset augmentation...")
    augmented_jsonl_str = augment_dataset(sample_jsonl, target_words=2000)

    temp_file = "temp_augmented.jsonl"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(augmented_jsonl_str)
    
    print(f"\n✅ Augmented dataset written to {temp_file}")
    print("Waiting 10 seconds before asking to delete...")
    time.sleep(10)

    choice = input("Do you want to delete the temp file? (y/n): ").strip().lower()
    if choice == "y":
        os.remove(temp_file)
        print("🗑️ Temp file deleted.")
    else:
        print(f"📂 Temp file kept at {temp_file}")


if __name__ == "__main__":
    main()