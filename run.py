import argparse
import subprocess
import time

API_KEYS = [
    "gsk_xxx", 
    "gsk_yyy", 
    "gsk_zzz"
]

def search(query, results, words):
    return subprocess.run(["python3", "search.py", "--word", query, "--max-results", str(results), "--max-words", str(words)], capture_output=True, text=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--words", default="words.txt")
    parser.add_argument("--startidx", type=int, required=True)
    parser.add_argument("--endidx", type=int, required=True)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()

    with open(args.words, encoding="utf-8") as f:
        words = [x.strip() for x in f if x.strip()]

    for i, word in enumerate(words[args.startidx - 1:args.endidx], args.startidx):
        print(f"[{i}] {word}")

        results = "\n\n".join([
            search(f"{word} define", 5, 200),
            search(f"{word} etymology", 10, 200),
            search(f"{word} collocations", 10, 100),
            search(f"{word} reverso", 3, 200),
        ])

        with open(args.output, "a", encoding="utf-8") as f:
            subprocess.run(["python3", "vocab.py", "--word", word, "--api-key", API_KEYS[(i - 1) % len(API_KEYS)], "--prompt", args.prompt, "--scrape-result", results], stdout=f, check=True)

        if i < args.endidx:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
