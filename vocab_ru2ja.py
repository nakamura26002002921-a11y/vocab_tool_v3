import argparse
import csv
import json
import sys
from groq import Groq

PROMPT = """
ロシア語の単語「{word}」について、以下のWeb検索結果を参考にして情報を整理してください。

【Web検索結果】
{scrape_result}

以下のJSON形式で出力してください。

{
  "word": "単語",
  "meaning": "日本語訳",
  "part_of_speech": "品詞",
  "etymology": "語源",
  "collocations": ["コロケーション1", "コロケーション2", "コロケーション3"],
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--scrape-result", required=True)
    args = parser.parse_args()

    prompt = PROMPT.format(word=args.word, scrape_result=args.scrape_result)

    client = Groq(api_key=args.api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)

    csv.writer(sys.stdout).writerow([
        data["word"],
        data["meaning"],
        data["part_of_speech"],
        data["etymology"],
        "; ".join(data["collocations"]),
        data["example"],
        data["example_translated"],
    ])


if __name__ == "__main__":
    main()
