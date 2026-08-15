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
目的：
ロシア語学習者が単語の意味・使い方・語源を理解し、実際のロシア語で自然に使えるようにするための語彙データを作成する。辞書的な情報だけでなく、現代ロシア語として自然で実用的な表現を重視する。

Web検索結果を最優先し、確認できない情報は推測しない。対象単語と直接関係する情報だけを使用し、類似語・同義語・別語の情報を混同しない。

- word: 入力された対象単語をそのまま使用
- meaning: 短い訳語、最大3項目、各10字程度、「；」で区切る
- part_of_speech: 英語の品詞名
- etymology: ロシア語としての語源・由来を日本語で記載。確認できない場合は空文字列
- collocations: 確認できた自然なロシア語のコロケーションを最大3つ。「ロシア語（日本語訳）」形式。確認できない場合は空配列
- examples: 自然で実際に使われるロシア語の例文を必ず2つ作成。可能なら異なる用法を使用
- example_translated: 対応する自然で正確な日本語訳

すべてのフィールドは指定されたJSON Schemaの型を厳密に守る。
JSON以外の文章を出力しない。
"""


SCHEMA = {
    "type": "object",
    "properties": {
        "word": {"type": "string"},
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
            "minItems": 2,
            "maxItems": 2
        }
    },
    "required": ["word", "meaning", "part_of_speech", "etymology", "collocations", "examples"],
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
        temperature=0,
        max_tokens=2000,
        response_format={"type": "json_schema", "json_schema": {"name": "russian_vocab", "strict": True, "schema": SCHEMA}}
    )
    return json.loads(response.choices[0].message.content)


def search(query, results, max_chars, timeout=10, unicode_start=None, unicode_end=None):
    cmd = ["python3", "search.py", "--word", query, "--max-results", str(results), "--max-chars", str(max_chars), "--timeout", str(timeout)]
    if unicode_start is not None: cmd += ["--unicode-start", hex(unicode_start)]
    if unicode_end is not None: cmd += ["--unicode-end", hex(unicode_end)]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout

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
                search(f"{word} значение", 3, 1500, 10, 0x0400, 0x04FF),
                search(f"{word} происхождение этимология", 3, 1500, 10, 0x0400, 0x04FF)
            ])
            data = call_vocab(PROMPT.format(word=word, results=results), api_key)
            collocations = data.get("collocations", [])[:3]
            examples = data.get("examples", [])

            with open(args.output, "a", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow([
                    data.get("word", word),
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
