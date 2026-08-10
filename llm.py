import argparse
import csv
import json
import sys
from groq import Groq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    client = Groq(api_key=args.api_key)

    prompt = f"""
英単語「{args.word}」について、以下をJSONで返してください。

word: 単語
meaning_ja: 日本語訳
etymology: 語源
collocations: 代表的なコロケーション3つ
example_en: 自然な英語の例文
example_ja: 例文の日本語訳

JSONのみ出力してください。
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)

    csv.writer(sys.stdout).writerow([
        data["word"],
        data["meaning_ja"],
        data["etymology"],
        data["collocations"],
        data["example_en"],
        data["example_ja"],
    ])


if __name__ == "__main__":
    main()

