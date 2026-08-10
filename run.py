```python
import argparse
import subprocess
import time


API_KEYS = [
    "gsk_xxxxxxxxxxxxxxxxx",
    "gsk_yyyyyyyyyyyyyyyyy",
    "gsk_zzzzzzzzzzzzzzzzz",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--words", default="words.txt")
    parser.add_argument("--startidx", type=int, required=True)
    parser.add_argument("--endidx", type=int, required=True)
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    with open(args.words, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]

    start = args.startidx - 1
    end = min(args.endidx, len(words))

    for i in range(start, end):
        word = words[i]
        api_key = API_KEYS[i % len(API_KEYS)]

        print(f"[{i + 1}/{len(words)}] {word}")

        results = []

        for query in [
            f"{word} define",
            f"{word} etymology",
            f"{word} collocations",
        ]:
            result = subprocess.run(
                ["python3", "search.py", "--word", query],
                capture_output=True,
                text=True,
                check=True,
            )
            results.append(result.stdout)

        with open(args.output, "a", encoding="utf-8") as output:
            result = subprocess.run(
                [
                    "python3",
                    "vocab.py",
                    "--word",
                    word,
                    "--api-key",
                    api_key,
                    "--scrape-result",
                    "\n\n".join(results),
                ],
                stdout=output,
                check=True,
            )

        if i < end - 1:
            print(f"Waiting {args.interval} seconds...")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
```
