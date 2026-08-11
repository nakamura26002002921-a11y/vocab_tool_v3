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

ロシア語話者向けに、日本語の単語を学習するための辞書データを作成してください。

# 対象単語

{word}

# Web検索結果

{results}

# 制約条件

Web検索結果を最優先し、確認できない情報は推測しない。対象単語と直接関係する情報のみを使用し、類似語・同義語・関連語・同じ漢字を使う別語の情報を混同しない。「word」は入力値「{word}」をそのまま使用し、表記や読みを変更しない。「reading」は「word」自体の自然な読みをひらがなだけで記載する。「meaning」は対象単語の現代日本語として一般的な意味をロシア語で最大3つ記載し、同じ意味の言い換えを重複させない。「part_of_speech」は対象単語そのものの品詞を英語で記載する。「etymology」は対象単語の日本語としての語源・由来または漢字の成り立ちをロシア語で記載し、語源と漢字の字源を混同せず、確認できた情報だけを使用する。確証がない場合は推測しない。「collocations」は対象単語と実際に自然な組み合わせとして使用される日本語表現を確認できたものから最大3つ記載し、「日本語（ロシア語訳）」の形式とする。「examples」は対象単語そのものの一般的かつ自然な用法を使用した日本語例文を必ず2つ作成し、「example_translated」には対応する自然で正確なロシア語訳を記載する。「collocations」と「examples」の日本語部分では、漢字を含む語・表現に必ず自然なひらがなの読みを「漢字を含む語・表現（ひらがなの読み）」の形式で付ける。漢字1文字ごとではなく自然な語・表現単位で読みを付け、読みの付け忘れを絶対に残さない。日本語部分のすべての漢字に読みが付いていることを確認してから出力する。「word」には読みを付けず、「reading」には読みだけを記載し、ロシア語には日本語のふりがなを付けない。確認できない情報は「""」または「[]」とし、推測で補完しない。

"""


def call_vocab(prompt, api_key):
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=2000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "japanese_vocab",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "word": {
                            "type": "string"
                        },
                        "reading": {
                            "type": "string"
                        },
                        "meaning": {
                            "type": "string"
                        },
                        "part_of_speech": {
                            "type": "string"
                        },
                        "etymology": {
                            "type": "string"
                        },
                        "collocations": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "maxItems": 3
                        },
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "example": {
                                        "type": "string"
                                    },
                                    "example_translated": {
                                        "type": "string"
                                    }
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
                        "reading",
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
                search(f"{word} 意味", 3, 800),
                search(f"{word} 由来", 3, 800),
                search(f"{word} コロケーション", 5, 1000),
                search(f"{word} 例文", 5, 1000)
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
