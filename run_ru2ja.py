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

日本語話者向けに、ロシア語の単語を学習するための辞書データを作成してください。

# 対象単語

{word}

# Web検索結果

{results}

# 出力形式

以下のJSON形式で出力してください。

{{
  "word": "{word}",
  "meaning": "日本語での意味",
  "part_of_speech": "英語の品詞名",
  "etymology": "ロシア語としての語源・由来",
  "collocations": [
    "ロシア語のコロケーション（日本語訳）"
  ],
  "examples": [
    {{
      "example": "自然なロシア語の例文",
      "example_translated": "例文の自然な日本語訳"
    }},
    {{
      "example": "自然なロシア語の例文",
      "example_translated": "例文の自然な日本語訳"
    }}
  ]
}}

# 制約条件

Web検索結果を最優先し、確認できない情報は推測しない。類似語・同義語・別語の情報を混同しない。「word」は入力値「{word}」をそのまま使う。
「meaning」は日本語で代表的な意味を最大3つ記載し、複数は「;」で区切る。確認できない場合は「""」とする。「part_of_speech」は英語で記載し、確認できない場合は「""」とする。「etymology」はロシア語としての語源・由来を100文字以内で記載し、確認できない場合は「""」とする。
「collocations」は確認できたものを最大3つ、「ロシア語（日本語訳）」の形式で記載する。3つ未満なら確認できたものだけとし、存在しないものは補完しない。確認できない場合は「[]」とする。
「examples」は必ず2つ作成する。「{word}」または自然な文法変化形を含む自然なロシア語とし、可能なら異なる用法を使う。「example_translated」は自然で正確な日本語訳とする。
JSONのみを出力し、JSON以外の文章やMarkdownコードブロックは出力しない。


# 出力例
# 出力例(домの場合)

{{
  "word": "дом",
  "meaning": "家; 家庭",
  "part_of_speech": "noun",
  "etymology": "古ロシア語に由来し、住居や家庭を表す語として発達した。",
  "collocations": [
    "строить дом（家を建てる）",
    "вернуться домой（家に帰る）",
    "жить с семьёй（家族と暮らす）"
  ],
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
"""

def call_vocab(prompt, api_key):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=1500)
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
                search(f"{word} значение", 3, 3000),
                search(f"{word} этимология", 3, 3000)
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
