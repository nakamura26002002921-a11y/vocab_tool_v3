import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    results = []

    for query in [
        f"{args.word} define",
        f"{args.word} etymology",
        f"{args.word} collocations",
    ]:
        result = subprocess.run(
            ["python3", "search.py", "--word", query],
            capture_output=True,
            text=True,
            check=True,
        )
        results.append(result.stdout)

    subprocess.run(
        [
            "python3",
            "vocab.py",
            "--word",
            args.word,
            "--api-key",
            args.api_key,
            "--scrape-result",
            "\n\n".join(results),
        ],
        check=True,
    )

if __name__ == "__main__":
    main()
