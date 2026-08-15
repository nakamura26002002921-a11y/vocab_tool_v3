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

import json
from groq import Groq


SYSTEM_PROMPT = """
あなたは、ロシア語話者向けの日本語学習用辞書データを作成する専門家です。

【基本方針】
- Web検索結果を最優先する。
- 確認できない情報は推測しない。
- 対象単語そのものについてのみ回答する。
- 類似語・同義語・関連語・同じ漢字を使う別語の情報を混同しない。

【word】
- 入力値をそのまま使用する。
- 表記や読みを変更しない。
- 読みを付けない。

【reading】
- word自体の自然な読みをひらがなだけで記載する。

【meaning】
- 対象単語の現代日本語として一般的な意味をロシア語で記載する。
- 最大3つ。
- 同じ意味の言い換えを重複させない。

【part_of_speech】
- 対象単語そのものの品詞を英語で記載する。

【etymology】
- 対象単語の日本語としての語源・由来または漢字の成り立ちをロシア語で記載する。
- 語源と漢字の字源を混同しない。
- 確認できない場合は推測せず空文字にする。

【collocations】
- 対象単語と自然に組み合わせて使用される日本語表現を最大3つ記載する。
- 「日本語（ロシア語訳）」の形式にする。
- 漢字を含む日本語には自然な語・表現単位でひらがなの読みを付ける。

【examples】
- 対象単語そのものを使用した自然な日本語例文を2つ作成する。
- exampleには日本語を記載する。
- example_translatedには自然で正確なロシア語訳を記載する。
- 日本語部分に含まれる漢字には必ず自然な単位でひらがなの読みを付ける。
- ロシア語には日本語のふりがなを付けない。

【不確かな情報】
- 確認できない情報は推測で補完しない。
- 文字列は空文字、配列は空配列にする。
"""


VOCAB_SCHEMA = {
    "type": "object",
    "properties": {
        "word": {"type": "string"},
        "reading": {"type": "string"},
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
        "reading",
        "meaning",
        "part_of_speech",
        "etymology",
        "collocations",
        "examples"
    ],
    "additionalProperties": False
}


def call_vocab(word, results, api_key):
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"対象単語:\n{word}\n\n"
                    f"Web検索結果:\n{results}"
                )
            }
        ],

        temperature=0,
        max_tokens=2000,

        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "japanese_vocab",
                "strict": True,
                "schema": VOCAB_SCHEMA
            }
        }
    )

    # キャッシュ状況を確認
    usage = response.usage

    prompt_tokens = usage.prompt_tokens
    cached_tokens = 0

    if usage.prompt_tokens_details:
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    if prompt_tokens > 0:
        cache_rate = cached_tokens / prompt_tokens * 100
    else:
        cache_rate = 0

    print(
        f"[Groq] "
        f"prompt={prompt_tokens}, "
        f"cached={cached_tokens}, "
        f"cache_rate={cache_rate:.1f}%"
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
