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

Web検索結果を最優先し、確認できない情報は推測しない。類似語・同義語・別語の情報を混同せず、対象単語と直接関係する情報だけを使用する。
「word」は入力値「{word}」をそのまま使用する。表記を変更しない。読みを付けない。
「reading」は「word」の自然な日本語の読みを、ひらがなだけで記載する。カタカナ・漢字・ローマ字は使用しない。確認できない場合は「""」とする。
「meaning」は日本語の代表的な意味をロシア語で最大3つ記載する。複数の意味は「;」で区切る。確認できない場合は「""」とする。
「part_of_speech」は英語の品詞名で記載する。確認できない場合は「""」とする。
「etymology」は漢字の成り立ち、日本語としての語源・由来などをロシア語で記載する。100文字以内を目安とする。Web検索結果で確認できない情報は推測しない。諸説ある場合は確認できた説だけを記載する。確認できない場合は「""」とする。
「collocations」はWeb検索で確認できた自然な日本語のコロケーションを最大3つ記載する。「日本語（ロシア語訳）」の形式とする。日本語部分の漢字には、すべて「漢字（ひらがな）」形式で読みを付ける。例：「家（いえ）を建（た）てる（построить дом）」。確認できたものが3つ未満の場合は、確認できたものだけを記載する。推測で補完しない。確認できない場合は「[]」とする。
「examples」は必ず2つ作成する。「{word}」またはその自然な活用形を含む、自然で実際に使われる日本語の例文とする。可能であれば異なる用法を使用する。例文中のすべての漢字に「漢字（ひらがな）」形式で読みを付ける。例：「仕事（しごと）が終（お）わったら家（いえ）に帰（かえ）ります。」。
「example_translated」は対応する日本語例文の自然で正確なロシア語訳とする。ロシア語で記載し、日本語のふりがなは付けない。
日本語を含むフィールドでは、原則としてすべての漢字にひらがなの読みを付ける。ただし「word」は入力値をそのまま使用する。「reading」は読みだけをひらがなで記載する。
Web検索結果で確認できない情報を一般知識だけで補完しない。特に語源・漢字の成り立ちは慎重に扱い、確証がない場合は推測しない。確認できない場合は、該当フィールドを「""」または「[]」とする。
JSON Schemaで指定された構造を厳密に守る。JSON以外の文章を出力しない。Markdownコードブロックを使用しない。指定されたキー名を変更しない。
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
                search(f"{word} 意味", 2, 600),
                search(f"{word} 由来", 2, 1000)
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
