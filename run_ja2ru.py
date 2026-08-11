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

Web検索結果を最優先し、確認できない情報は推測しない。類似語・同義語・別語を混同せず、対象単語に直接関係する情報だけを使用する。情報を確認できない場合は、該当フィールドを「""」または「[]」とする。
「word」は入力値「{word}」をそのまま使用し、表記や漢字を変更せず、読みも付けない。
「reading」は「word」の自然な読みをひらがなだけで記載する。確認できない場合は「""」とする。
「meaning」は「word」の代表的な意味をロシア語で最大3つ記載し、複数は「;」で区切る。確認できない場合は「""」とする。
「part_of_speech」は英語の品詞名で記載する。確認できない場合は「""」とする。
「etymology」は漢字の成り立ち、日本語としての語源・由来などをロシア語で最大100ロシア語単語程度で記載する。漢字の字源と日本語の語源を混同せず、Web検索で確認できた説だけを記載する。確認できない場合は「""」とする。
「collocations」はWeb検索で確認できた自然なコロケーションを最大3つ、「日本語（ロシア語訳）」の形式で記載する。存在しないものを推測して補完しない。確認できない場合は「[]」とする。
「examples」は必ず2つ作成し、「{word}」または自然な活用形を含む自然な日本語の例文とする。可能であれば異なる用法を使用する。
「example_translated」は各例文の自然で正確なロシア語訳とする。
日本語を含む「collocations」「examples」では、漢字を含む語・表現に自然なひらがなの読みを付ける。漢字1文字ごとに機械的に付けず、語・表現単位で付ける。例えば「青二才（あおにさい）」「青空（あおぞら）」「仕事（しごと）が終（お）わる」のように記載する。ひらがな・カタカナ・ローマ字には読みを付けない。
「example_translated」などのロシア語には日本語のふりがなを付けない。
JSON Schemaで指定された構造とキー名を厳密に守る。JSON以外の文章やMarkdownコードブロックを出力しない。

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
