import argparse
import csv
import json
import subprocess
import sys
import time

API_KEYS = [
    "gsk_xxx",
    "gsk_yyy",
    "gsk_zzz",
]

PROMPT = """
日本語話者向けのロシア語辞書データを作成してください。

対象単語: 「{word}」

以下のWeb検索結果を参考にしてください。

【検索結果】
{results}

以下のJSONのみを出力してください。

{{
  "word": "{word}",
  "meaning": "日本語訳。多義語の場合は代表的な意味を最大3つまで「;」で区切る。確認できない場合は空文字。",
  "part_of_speech": "品詞を英語で記載。確認できない場合は空文字。",
  "etymology": "語源・由来を50文字以内で簡潔に記載。確認できない場合は空文字。",
  "collocations": ["確認できた代表的なコロケーションを最大3つ。3つ未満なら確認できたものだけ。存在しない場合は空配列。"],
  "examples": [
    {{
      "example": "対象単語「{word}」または自然な活用形を含む自然なロシア語の例文",
      "example_translated": "例文の自然な日本語訳"
    }},
    {{
      "example": "対象単語「{word}」または自然な活用形を含む自然なロシア語の例文",
      "example_translated": "例文の自然な日本語訳"
    }}
  ]
}}

【出力例】

入力単語:
дом

出力:
{{
  "word": "дом",
  "meaning": "家; 家庭",
  "part_of_speech": "noun",
  "etymology": "古ロシア語に由来する語",
  "collocations": ["жить в доме", "родной дом", "строить дом"],
  "examples": [
    {{
      "example": "Я возвращаюсь домой после работы.",
      "example_translated": "私は仕事の後に家に帰ります。"
    }},
    {{
      "example": "Этот дом очень старый.",
      "example_translated": "この家はとても古いです。"
    }}
  ]
}}

ルール:
- Web検索結果を最優先し、確認できない情報は推測しない。
- 類似語・同義語・別の単語の情報を混同しない。
- "word" は入力された「{word}」をそのまま使用する。
- JSON以外は出力しない。
"""

def search(query, results, words):
    return subprocess.run(
        [
            "python3",
            "search.py",
            "--word",
            query,
            "--max-results",
            str(results),
            "--max-words",
            str(words),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def call_vocab(word, results, api_key):
    prompt = PROMPT.format(word=word, results=results)

    result = subprocess.run(
        [
            "python3",
            "vocab.py",
            "--prompt",
            prompt,
            "--api-key",
            api_key,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


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

    for i, word in enumerate(
        words[args.startidx - 1:args.endidx],
        args.startidx,
    ):
        print(f"[{i}] {word}")

        api_key = API_KEYS[(i - 1) % len(API_KEYS)]

        try:
            results = "\n\n".join([
                search(f"{word} значение", 5, 100),
                search(f"{word} этимология", 10, 200),
                search(f"{word} коллокации", 10, 100),
                search(f"{word} примеры предложений", 3, 1000),
            ])

            data = call_vocab(word, results, api_key)

            collocations = data.get("collocations", [])[:3]
            examples = data.get("examples", [])

            with open(
                args.output,
                "a",
                encoding="utf-8",
                newline="",
            ) as f:
                csv.writer(f).writerow([
                    data.get("word", word),
                    data.get("meaning", ""),
                    data.get("part_of_speech", ""),
                    data.get("etymology", ""),
                    "; ".join(collocations),
                    examples[0].get("example", "") if len(examples) > 0 else "",
                    examples[0].get("example_translated", "") if len(examples) > 0 else "",
                    examples[1].get("example", "") if len(examples) > 1 else "",
                    examples[1].get("example_translated", "") if len(examples) > 1 else "",
                ])

            print(f"[{i}] OK")

        except Exception as e:
            print(f"[{i}] ERROR: {e}", file=sys.stderr)

        if i < args.endidx:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
