import os
import json
import unicodedata

def tostring(number: int) -> str:
    return str(number)

def clean_unicode(text: str) -> str:
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",     # en dash
        "—": "-",     # em dash
        "…": "...",   # ellipsis
        "•": "-",     # bullet
        " ": " ",     # narrow no-break space
        "\u00A0": " ",  # non-breaking space
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = unicodedata.normalize('NFKC', text)
    return text

def count_words_in_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()
        text = clean_unicode(text)
        words = text.split()
        return len(words)

def process_lines(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [clean_unicode(line.strip()) for line in f if line.strip()]
        result = [{"name": tostring(i + 1), "text": line, "duration": 1} for i, line in enumerate(lines)]
        return result

def main():
    filename = "words.txt"
    if not os.path.exists(filename):
        print(f"File '{filename}' not found.")
        return

    total_words = count_words_in_file(filename)
    print(f"You have {total_words} words. Generate output? (y/n): ", end='')
    choice = input().strip().lower()

    if choice == 'y':
        result = process_lines(filename)
        with open("supabase_words.txt", "w", encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)  # allow emoji & foreign chars
        print("Output written to supabase_words.txt")
    else:
        print("Generation cancelled.")

if __name__ == "__main__":
    main()
