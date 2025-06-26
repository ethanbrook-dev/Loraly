import os
import json

def tostring(number: int) -> str:
    return str(number)  # Just convert to string without extra spaces

def count_words_in_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()
        words = text.split()
        return len(words)

def process_lines(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
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
            json.dump(result, f, indent=2)  # Write JSON with double quotes nicely formatted
        print("Output written to supabase_words.txt")
    else:
        print("Generation cancelled.")

if __name__ == "__main__":
    main()
