import argparse
import csv
import json
import subprocess
import time

from groq import Groq

API_KEYS = [
    "gsk_xxx",
    "gsk_yyy",
    "gsk_zzz",
]

PROMPT = """
ロシア語の単語「{word}」について、以下のWeb検索結果を参考にして情報を整理してください。

【Web検索結果】
{results}

以下のJSON形式で出力してください。

{
  "word": "ロシア語の単語",
  "meaning": "日本語訳",
  "part_of_speech": "品詞",
  "etymology": "語源",
  "collocations": [
    "代表的なコロケーション1",
    "代表的なコロケーション2",
    "代表的なコロケーション3"
  ],
  "example": "自然なロシア語の例文",
  "example_translated": "例文の日本語訳"
}

ルール:
- Web検索結果の情報を優先する
- 情報がない場合は無理に推測しない
- 語源は簡潔にする
- 品詞は英語で記載する
- コロケーションは3つ
- 例文は自然なロシア語にする
- JSONのみ出力する
"""


def search(query, max_results, max_words):
    result = subprocess.run(
        [
            "python3",
            "search.py",
            "--word",
            query,
            "--max-results",
            str(max_results),
            "--max-words",
            str(max_words),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


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

        results = "\n\n".join([
            search(f"{word} значение", 5, 1000),
            search(f"{word} этимология", 10, 1000),
            search(f"{word} сочетаемость", 10, 100),
            search(f"{word} reverso", 3, 1000),
        ])

        prompt = PROMPT.format(
            word=word,
            results=results,
        )

        client = Groq(api_key=API_KEYS[(i - 1) % len(API_KEYS)])

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        data = json.loads(response.choices[0].message.content)

        with open(args.output, "a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([
                data["word"],
                data["meaning"],
                data["part_of_speech"],
                data["etymology"],
                "; ".join(data["collocations"]),
                data["example"],
                data["example_translated"],
            ])

        if i < args.endidx:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
