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

PROMPT = """
# 目的

日本語話者がロシア語の単語を正確に学習できる辞書データを作成する。Web検索結果を根拠として、意味・語源・コロケーション・例文を正確に整理する。

# 対象単語

{word}

# Web検索結果

{results}

# 制約条件

Web検索結果を最優先し、確認できない情報は推測しない。対象単語と直接関係する情報だけを使用し、類似語・同義語・別語の情報を混同しない。「word」は入力値「{word}」をそのまま使用する。「meaning」は短い訳語、最大3項目、各10字程度、「;」で区切る。「part_of_speech」は英語の品詞名で記載する。「etymology」はロシア語としての語源・由来を日本語で記載し、確認できない場合は空文字列とする。「collocations」は確認できた自然なロシア語のコロケーションを最大3つ、「ロシア語（日本語訳）」の形式で記載し、確認できない場合は空配列とする。「examples」は自然で実際に使われるロシア語の例文を必ず2つ作成し、可能なら異なる用法を使用する。「example_translated」は対応する自然で正確な日本語訳とする。すべてのフィールドは指定されたJSON Schemaの型を厳密に守る。JSON以外の文章を出力しない。

"""

def call_vocab(prompt, api_key):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=2000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "russian_vocab",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string"},
                        "meaning": {"type": "string"},
                        "part_of_speech": {"type": "string"},
                        "etymology": {"type": "string"},
                        "collocations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 3
                        },
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "example": {"type": "string"},
                                    "example_translated": {"type": "string"}
                                },
                                "required": [
                                    "example",
                                    "example_translated"
                                ],
                                "additionalProperties": False
                            },
                            "minItems": 2,
                            "maxItems": 2
                        }
                    },
                    "required": [
                        "word",
                        "meaning",
                        "part_of_speech",
                        "etymology",
                        "collocations",
                        "examples"
                    ],
                    "additionalProperties": False
                }
            }
        }
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
