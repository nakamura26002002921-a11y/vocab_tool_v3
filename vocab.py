import argparse
import csv
import json
import sys
from groq import Groq

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--scrape-result", required=True)
    
    args = parser.parse_args()
    
    client = Groq(api_key=args.api_key)

    prompt = f"""
英単語「{args.word}」について、以下のWeb検索結果を参考にして情報を整理してください。

【Web検索結果】
{args.scrape_result}

以下のJSON形式で出力してください。

{{
  "word": "単語",
  "meaning_ja": "日本語訳",
  "etymology": "語源",
  "collocations": ["コロケーション1", "コロケーション2", "コロケーション3"],
  "example_en": "自然な英語の例文",
  "example_ja": "例文の日本語訳"
}}

ルール:
- Web検索結果の情報を優先する
- 情報がない場合は無理に推測しない
- 語源は簡潔にする
- コロケーションは3つ
- 例文は自然な英文にする
- JSONのみ出力する
"""

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
        data["meaning_ja"],
        data["etymology"],
        "; ".join(data["collocations"]),
        data["example_en"],
        data["example_ja"],
    ])


if __name__ == "__main__":
    main()
