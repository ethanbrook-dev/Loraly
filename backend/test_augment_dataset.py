import json
import os
import re
from .augment_dataset import augment_dataset

pronoun_re = re.compile(r"\b(I|you|we|they|he|she|it|me|us|him|her)\b", re.I)
verb_re = re.compile(
    r"\b(am|is|are|was|were|have|has|had|do|does|did|go|going|went|will|can|could|should|need|want|love|like|hate|see|come|leave|arrive|text|call|meet|sleep|eat|drink|work|study|watch|play)\b",
    re.I
)

MIN_WORDS = 2

def count_words(text):
    return len([w for w in text.split() if w.strip()])

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
    
def jaccard_similarity(a, b):
    a_set, b_set = set(a.split()), set(b.split())
    if not a_set and not b_set:
        return 1.0
    return len(a_set & b_set) / len(a_set | b_set)

def dataset_consistency(original_jsonl, augmented_jsonl, is_grammatical):
    original = [json.loads(l)["messages"] for l in original_jsonl.strip().split("\n")]
    augmented = [json.loads(l)["messages"] for l in augmented_jsonl.strip().split("\n")]
    
    similarities = []
    grammar_pass = 0
    role_lengths = {"user": [], "assistant": []}
    
    for orig_conv, aug_conv in zip(original, augmented):
        for o_msg, a_msg in zip(orig_conv, aug_conv):
            # role consistency check
            if o_msg["role"] != a_msg["role"]:
                print(f"Role mismatch: {o_msg} vs {a_msg}")
            
            # word overlap
            sim = jaccard_similarity(o_msg["content"], a_msg["content"])
            similarities.append(sim)
            
            # grammar check
            if is_grammatical(a_msg["content"]):
                grammar_pass += 1
            
            # length tracking
            role_lengths[o_msg["role"]].append(len(a_msg["content"].split()))
    
    avg_similarity = sum(similarities) / len(similarities)
    grammar_rate = grammar_pass / sum(len(conv) for conv in augmented)
    avg_lengths = {role: sum(lens)/len(lens) if lens else 0 for role, lens in role_lengths.items()}
    
    return {
        "avg_jaccard_similarity": avg_similarity,
        "grammar_pass_rate": grammar_rate,
        "avg_message_lengths": avg_lengths
    }
    
def run_test(path: str = "original_input.jsonl"):
    
    if not os.path.exists(path):
        print(f"Test file {path} does not exist.")
        return
    
    with open(path, "r", encoding="utf-8") as f:
        original_jsonl = f.read()
    
    augmented_jsonl = augment_dataset(original_jsonl, target_words=200_000)
    
    results = dataset_consistency(original_jsonl, augmented_jsonl, is_grammatical)
    print("Dataset Consistency Results:")
    print(json.dumps(results, indent=2))
    

if __name__ == "__main__":
    run_test()