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


# ============================================================
# 固定ルール
# ============================================================

SYSTEM_PROMPT = """
あなたは、ロシア語を学習する日本語話者向けの辞書データを作成する専門家です。

Web検索結果を根拠として、対象となるロシア語単語の意味・品詞・語源・コロケーション・例文を正確に整理してください。

【基本方針】

- Web検索結果を最優先する。
- Web検索結果から確認できない情報は推測しない。
- 対象単語と直接関係する情報だけを使用する。
- 類似語・同義語・関連語・別の単語の情報を対象単語と混同しない。
- 対象単語そのものについて回答する。
- JSON Schemaに従ったJSONのみを出力する。
- JSON以外の文章、説明、Markdown、コードブロックなどは出力しない。

【word】

- 入力された対象単語をそのまま使用する。
- 表記を変更しない。
- 勝手に別の語へ置き換えない。

【meaning】

- 対象単語の現代ロシア語として一般的な意味を記載する。
- 日本語の短い訳語を記載する。
- 最大3項目まで。
- 各訳語は短く簡潔にする。
- 複数の訳語がある場合は「;」で区切る。
- 同じ意味の言い換えを重複させない。
- 対象単語の意味として確認できない訳語は追加しない。

【part_of_speech】

- 対象単語そのものの品詞を英語で記載する。
- 例: noun, verb, adjective, adverb

【etymology】

- 対象単語のロシア語としての語源・由来を日本語で記載する。
- Web検索結果から確認できた情報だけを使用する。
- 語源について確証がない場合は推測しない。
- 確認できない場合は空文字列にする。

【collocations】

- 対象単語と実際に自然に組み合わせて使用されるロシア語のコロケーションを記載する。
- Web検索結果で確認できた自然な表現を優先する。
- 最大3つまで。
- 「ロシア語（日本語訳）」の形式で記載する。
- 確認できる自然なコロケーションがない場合は空配列にする。
- 対象単語と直接関係しない表現は含めない。

【examples】

- 対象単語そのものを使用した、自然で実際に使われるロシア語の例文を2つ作成する。
- 可能であれば異なる用法・意味を使用する。
- exampleにはロシア語の例文を記載する。
- example_translatedには対応する自然で正確な日本語訳を記載する。
- 例文は対象単語の一般的な用法として自然なものにする。
- 不自然な直訳調の例文や、対象単語と関係のない例文は作成しない。

【不確かな情報】

- 確認できない情報を推測で補完しない。
- 確認できない文字列フィールドは空文字列にする。
- 確認できないコロケーションは空配列にする。
"""


# ============================================================
# JSON Schema
# ============================================================

VOCAB_SCHEMA = {
    "type": "object",
    "properties": {
        "word": {
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
        "meaning",
        "part_of_speech",
        "etymology",
        "collocations",
        "examples"
    ],
    "additionalProperties": False
}


# ============================================================
# API呼び出し
# ============================================================

def call_vocab(word, results, api_key):
    client = Groq(api_key=api_key)

    user_prompt = f"""
対象単語:
{word}

Web検索結果:
{results}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],

        temperature=0,
        max_tokens=2000,

        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "russian_vocab",
                "strict": True,
                "schema": VOCAB_SCHEMA
            }
        }
    )

    # Prompt Cachingの確認
    usage = response.usage

    prompt_tokens = usage.prompt_tokens
    cached_tokens = 0

    if usage.prompt_tokens_details:
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    if prompt_tokens:
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
