# Dataset Augmentation Plan

## Introduction
This document describes the strategy for augmenting small chat datasets into much larger ones while preserving the style, habits, and personalities of the original participants. The approach is designed for training dynamic LoRA adapters, where consistency and authenticity are crucial.

For example, starting with an 8.8k word WhatsApp chat, the pipeline can generate ~200k words of augmented dialogue that looks and feels identical to the original conversation. This results in a dataset that is large enough for effective training while maintaining the exact tone, slang, emojis, and interaction patterns of the participants.

## Purpose
The purpose of dataset augmentation is to expand a small chat dataset (e.g., 8.8k words) into a much larger one (e.g., ~200k words) while **preserving the exact style and personality of the participants**. A larger dataset makes the model **more consistent, accurate, and reliable**, because it has more examples of the way participants actually speak. By staying true to the original phrasing, slang, emojis, and turn-taking patterns, the augmented data ensures that the trained model reflects the same style without "drifting" into generic or out-of-character text.

## High-Level Strategy

### 1. Style-Preserving Variants & Turn-Taking Analysis
**Valid variants only:**
- A greeting or word variant is only included if it appears in the dataset.
- For **slang terms** (e.g., "yo", "ayy"), require at least **5 occurrences** before they're considered valid variants.
- Example: If the chat has "hello", "hey", "yo", and "ayy", those become valid options. If "hi" never appears, it is excluded.

**Slang, emojis, and punctuation frequency:**
- Compute how often slang, repeated emojis, or punctuation (e.g., "??", "!!") are used.
- Preserve these habits by inserting them at the same percentage frequency in augmented samples.

**Turn-taking & block patterns:**
- Measure **average message length per participant**.
- Track the ratio of short vs long replies.
- Capture interaction patterns (e.g., *User often replies with 1–2 words, then Assistant gives longer responses*).

**Output:** A "style profile" per participant capturing:
- Valid lexical variants
- Emoji & punctuation frequencies
- Turn-taking statistics
- Average reply lengths

### 2. Synonym Replacement & Message Re-Mixing
**Synonym replacement:**
- Only swap words with **variants actually present in the participant's messages**.
- Example: If "hello", "hey", and "yo" appear in the dataset, rotate between these. 
- **Never** invent new synonyms.

**Phrase expansion / re-mixing:**
- Break or merge messages to create variety.
- Examples:
  - "hey what's up" → "hey" + "what's up"
  - "I'm good" + "how about you?" → "I'm good, how about you?"

**Randomized sequencing:**
- Reorder or repeat conversation blocks in plausible ways to expand dataset size.
- Always preserve participant roles (User vs Assistant).
- Approximate real timing patterns.

### 3. Augmentation Loop
- Repeat steps **2–3** until the target dataset size (e.g., ~200k words) is reached.
- Track:
  - Total words added
  - Original word count
  - Number of augmentation iterations
- Set a **maximum retry count** to avoid infinite loops.

### 4. Optional Noise Injection
Minor stylistic variation:
- Typos, dropped letters, casual abbreviations **only if they already exist in the chat**.
- Insert emojis in the same way the participant does.
- Avoid generic templates or new slang that wasn’t in the dataset.

### 5. Output Format
- Export augmented conversations in **JSONL format**, identical to what `main.py` expects. 
- Each entry looks like:
    ```json
    {
    "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
    }
    ```
- The augmented dataset should be **indistinguishable from real conversations** in both style and structure.

### 6. Adaptive Augmentation per LoRA
- Adjust augmentation based on each participant’s unique style:
- If they use long messages, emphasize long-form expansions.
- If they frequently use emojis, keep emoji frequency high.
- Weight **more frequent phrases higher** so common speech habits remain dominant.

✅ This plan ensures the augmented dataset is **large enough for training** while remaining **100% faithful to the original style** of the participants.