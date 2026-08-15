import argparse
import csv
import json
import subprocess
import sys
import time
from groq import Groq

API_KEYS = [
    "gsk_xxx",
    "gsk_yyy",
    "gsk_zzz",
]

SYSTEM_PROMPT = """
Web検索結果を最優先し、確認できない情報は推測しない。対象単語そのものの情報だけを使用し、類似語・同義語・別語と混同しない。
「word」は入力値をそのまま使用。「reading」は自然なひらがな読み。「meaning」は現代日本語の一般的な意味をロシア語で最大3つ。
「part_of_speech」は英語の品詞名。「etymology」は日本語としての語源・由来または漢字の成り立ちをロシア語で記載し、不明なら空文字列。
「collocations」は自然な日本語表現を最大3つ、「日本語（ロシア語訳）」で記載し、漢字にはひらがなの読みを付ける。
「examples」は対象単語を使った自然な日本語例文を2つ。「example」は日本語、「example_translated」はロシア語訳。日本語の漢字にはひらがなの読みを付ける。
不明な文字列は空文字列、配列は空配列とする。JSON以外は出力しない。
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "word": {"type": "string"},
        "reading": {"type": "string"},
        "meaning": {"type": "string"},
        "part_of_speech": {"type": "string"},
        "etymology": {"type": "string"},
        "collocations": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "example": {"type": "string"},
                    "example_translated": {"type": "string"}
                },
                "required": ["example", "example_translated"],
                "additionalProperties": False
            },
            "minItems": 2, "maxItems": 2
        }
    },
    "required": ["word", "reading", "meaning", "part_of_speech", "etymology", "collocations", "examples"],
    "additionalProperties": False
}

def call_vocab(word, results, api_key):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"対象単語:\n{word}\n\nWeb検索結果:\n{results}"}
        ],
        temperature=0, max_tokens=2000,
        response_format={"type": "json_schema", "json_schema": {"name": "japanese_vocab", "strict": True, "schema": SCHEMA}}
    )
    return json.loads(response.choices[0].message.content)


def search(query, results, max_chars):
    return subprocess.run(["python3", "search.py", "--word", query, "--max-results", str(results), "--max-chars", str(max_chars)], capture_output=True, text=True, check=True).stdout

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--words", default="words.txt")
    parser.add_argument("--startidx", type=int, required=True)
    parser.add_argument("--endidx", type=int, required=True)
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    with open(args.words, encoding="utf-8") as f:
        words = [x.strip() for x in f if x.strip()]

    for i, word in enumerate(words[args.startidx - 1:args.endidx], args.startidx):
        print(f"[{i}] {word}")
        api_key = API_KEYS[(i - 1) % len(API_KEYS)]

        try:
            results = "\n\n".join([
                search(f"{word} 意味", 2, 400),
                search(f"{word} 由来", 2, 400),
                search(f"{word} コロケーション", 3, 500),
                search(f"{word} 例文", 3, 500)
            ])
            data = call_vocab(PROMPT.format(word=word, results=results), api_key)
            collocations = data.get("collocations", [])[:3]
            examples = data.get("examples", [])

            with open(args.output, "a", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow([
                    data.get("word", word),
                    data.get("reading", ""),
                    data.get("meaning", ""),
                    data.get("part_of_speech", ""),
                    data.get("etymology", ""),
                    "; ".join(collocations),
                    examples[0].get("example", "") if len(examples) > 0 else "",
                    examples[0].get("example_translated", "") if len(examples) > 0 else "",
                    examples[1].get("example", "") if len(examples) > 1 else "",
                    examples[1].get("example_translated", "") if len(examples) > 1 else ""
                ])

            print(f"[{i}] OK")
        except Exception as e:
            print(f"[{i}] ERROR: {e}", file=sys.stderr)

        if i < args.endidx:
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
