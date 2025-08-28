import json
import random
import re
from collections import Counter, defaultdict

from .slang_terms import get_all_slang_terms

# ---------- TUNABLES ----------
USER_REPLACE_PROB = 0.97
ASSISTANT_REPLACE_PROB = 0.03
PHASE_STYLE_PROB = 0.35
PHASE_STRUCT_PROB = 0.12
MIN_WORDS = 2
# -------------------------------

def augment_dataset(jsonl_str: str, target_words: int = 200_000) -> str:
    """LoRA-agnostic conversational dataset augmentation."""

    with open("original_input.jsonl", "w", encoding="utf-8") as f:
        f.write(jsonl_str)

    # ---------- helpers ----------
    def count_words(text):
        return len([w for w in text.split() if w.strip()])

    pronoun_re = re.compile(r"\b(I|you|we|they|he|she|it|me|us|him|her)\b", re.I)
    verb_re = re.compile(
        r"\b(am|is|are|was|were|have|has|had|do|does|did|go|going|went|will|can|could|should|need|want|love|like|hate|see|come|leave|arrive|text|call|meet|sleep|eat|drink|work|study|watch|play)\b",
        re.I
    )

    def is_grammatical(text: str, reference_text: str = None) -> bool:
        """Return True if text is grammatical or matches original style."""
        text = (text or "").strip()
        if not text or count_words(text) < MIN_WORDS:
            return False

        # Style-aware: if reference exists and was slangy/fragmented, allow similar
        if reference_text:
            ref_words = reference_text.split()
            if count_words(reference_text) <= 4 or any(re.search(r"[^\w\s]", w) for w in ref_words):
                return True

        # Standard grammatical heuristics
        if verb_re.search(text) or pronoun_re.search(text):
            return True
        if len(text) <= 4 and text.isalpha():
            return True
        return False

    def preserve_case_replace(orig: str, repl: str) -> str:
        if orig.isupper():
            return repl.upper()
        if orig[0].isupper():
            return repl.capitalize()
        return repl

    def drop_vowels(word: str) -> str:
        if len(word) <= 3:
            return word
        core = word[1:-1]
        core = re.sub(r"[aeiouAEIOU]", "", core)
        return word[0] + core + word[-1]

    TYPO_MAP = {"gonna": "gon", "you": "u", "are": "r", "with": "w/", "tonight": "2nite", "okay": "ok"}
    FILLERS = get_all_slang_terms(lowercase=True)
    POS_EMOJI = ["😊", "😂", "🔥", "❤️", "😆"]
    NEG_EMOJI = ["😩", "💀", "🙄"]

    # ---------- Load dataset ----------
    conversations = []
    for line in jsonl_str.strip().split("\n"):
        if not line.strip():
            continue
        try:
            conv = json.loads(line)
            if "messages" in conv and isinstance(conv["messages"], list):
                conversations.append(conv)
        except Exception:
            continue

    if not conversations:
        return ""

    # Build dynamic style profiles per role
    style_profiles = defaultdict(lambda: {"variants": Counter(), "emoji_freq": Counter(), "message_lengths": []})
    slang_candidates = set(FILLERS or [])

    for conv in conversations:
        for msg in conv["messages"]:
            role = msg.get("role", "user")
            text = msg.get("content", "") or ""
            style_profiles[role]["message_lengths"].append(count_words(text))
            for w in text.lower().split():
                style_profiles[role]["variants"][w] += 1
            emojis = re.findall(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+", text)
            for e in emojis:
                style_profiles[role]["emoji_freq"][e] += 1

    for r, p in style_profiles.items():
        filtered = Counter({w: f for w, f in p["variants"].items() if f >= 2 or w in slang_candidates})
        style_profiles[r]["variants"] = filtered if filtered else p["variants"]

    # ---------- Augmentation primitives ----------
    def lexical_tweak(text: str, role: str) -> str:
        words = text.split()
        if not words:
            return text
        variants = style_profiles[role]["variants"]
        new_words = []
        for w in words:
            lw = re.sub(r"[^\w']", "", w.lower())
            out_word = w
            if lw and lw in variants and random.random() < (0.2 if role == "user" else 0.03):
                pool = list(variants.keys())
                weights = [variants[k] for k in pool]
                pick = random.choices(pool, weights=weights, k=1)[0]
                out_word = preserve_case_replace(w, pick)
            elif lw in TYPO_MAP and random.random() < (0.12 if role == "user" else 0.02):
                out_word = preserve_case_replace(w, TYPO_MAP[lw])
            new_words.append(out_word)
        return " ".join(new_words)

    def stylistic_tweak(text: str, role: str) -> str:
        text = text.strip()
        if FILLERS and random.random() < (PHASE_STYLE_PROB if role == "user" else PHASE_STYLE_PROB*0.15):
            filler = random.choice(FILLERS)
            if random.random() < 0.5:
                text = f"{filler} {text}"
            else:
                text = f"{text} {filler}"
        if random.random() < 0.12 and not re.search(r"[.!?]$", text):
            text += random.choice([".", "...", "!!", "?!"])
        if random.random() < (0.08 if role == "user" else 0.02):
            for k, v in TYPO_MAP.items():
                text = re.sub(rf"\b{k}\b", v, text, flags=re.I)
        if random.random() < (0.10 if role == "user" else 0.02):
            text += " " + random.choice(POS_EMOJI + NEG_EMOJI)
        return text

    def structural_remix(messages: list) -> list:
        new_msgs = []
        prev = None
        for msg in messages:
            role = msg.get("role", "user")
            text = (msg.get("content") or "").strip()
            words = text.split()
            if "," in text and len(words) > 8 and random.random() < 0.25:
                parts = [p.strip() for p in text.split(",") if p.strip()]
                for p in parts:
                    if len(p.split()) >= MIN_WORDS:
                        new_msgs.append({"role": role, "content": p})
            elif prev and prev["role"] == role and len(words) < 5 and random.random() < 0.2:
                cand = (prev["content"].rstrip(".!?") + " " + text).strip()
                if is_grammatical(cand, reference_text=prev["content"]):
                    prev["content"] = cand
                else:
                    new_msgs.append(msg)
                    prev = msg
            else:
                new_msgs.append(msg)
                prev = msg
        if len(new_msgs) > 3 and random.random() < 0.06:
            i = random.randint(1, len(new_msgs) - 2)
            a, b = new_msgs[i], new_msgs[i+1]
            if is_grammatical(a["content"], reference_text=a["content"]) and is_grammatical(b["content"], reference_text=b["content"]):
                new_msgs[i], new_msgs[i+1] = b, a
        return new_msgs

    def conversation_level_variant(conv: dict, intensity: float = 0.8) -> dict:
        new_conv = {"messages": []}
        for msg in conv["messages"]:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "user":
                t = lexical_tweak(text, role)
                if random.random() < intensity:
                    t = stylistic_tweak(t, role)
                if random.random() < 0.08:
                    t = " ".join(drop_vowels(w) if random.random() < 0.12 else w for w in t.split())
                if not is_grammatical(t, reference_text=text):
                    t = text
                new_conv["messages"].append({"role": role, "content": t})
            else:
                if random.random() < 0.06:
                    t = lexical_tweak(text, role)
                    t = stylistic_tweak(t, role) if random.random() < 0.25 else t
                    if not is_grammatical(t, reference_text=text):
                        t = text
                    new_conv["messages"].append({"role": role, "content": t})
                else:
                    new_conv["messages"].append({"role": role, "content": text})
        return new_conv

    # ---------- Main augmentation loop ----------
    original_word_count = sum(count_words(msg.get("content", "")) for conv in conversations for msg in conv["messages"])
    target = target_words
    if original_word_count >= target:
        return "\n".join(json.dumps(c, ensure_ascii=False) for c in conversations)

    augmented = list(conversations)
    total_words = original_word_count

    while total_words < target:
        base_conv = random.choice(conversations)
        conv_variant = conversation_level_variant(base_conv)
        if all(is_grammatical(m.get("content", ""), reference_text=orig.get("content", "")) 
               for m, orig in zip(conv_variant["messages"], base_conv["messages"])):
            augmented.append(conv_variant)
            total_words += sum(count_words(m.get("content", "")) for m in conv_variant["messages"])

    out_lines = [json.dumps(conv, ensure_ascii=False) for conv in augmented]
    print(f"\nFinal word count: {total_words} / {target} {'✅' if total_words >= target else '❌'}")
    return "\n".join(out_lines)
