import os

def count_words_in_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()
        words = text.split()
        return len(words)

def process_lines(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
        result = [{"name": str(i + 1), "text": line, "duration": 1} for i, line in enumerate(lines)]
        return result

def main():
    filename = "words.txt"
    if not os.path.exists(filename):
        print(f"File '{filename}' not found.")
        return

    total_words = count_words_in_file(filename)

    if total_words < 100_000:
        print(f"You need {100_000 - total_words} more words to reach the 100,000 minimum.")
    else:
        print(f"You have {total_words} words. File generated:")
        result = process_lines(filename)
        print(result)

if __name__ == "__main__":
    main()
