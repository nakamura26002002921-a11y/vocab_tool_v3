import argparse
import csv
import json
import sys
from groq import Groq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--scrape-result", required=True)
    args = parser.parse_args()

    with open(args.prompt, encoding="utf-8") as f:
        prompt = f.read().format(word=args.word, scrape_result=args.scrape_result)

    client = Groq(api_key=args.api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)

    csv.writer(sys.stdout).writerow([
        data["word"],
        data["meaning"],
        data["part_of_speech"],
        data["etymology"],
        "; ".join(data["collocations"]),
        data["example"],
        data["example_translated"],
    ])


if __name__ == "__main__":
    main()
