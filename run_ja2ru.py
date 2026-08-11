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
# 目的

ロシア語話者向けに、日本語の単語を学習するための辞書データを作成してください。

# 対象単語

{word}

# Web検索結果

{results}

# 出力形式

以下のJSON形式で出力してください。

{{
  "word": "{word}",
  "meaning": "ロシア語での意味",
  "part_of_speech": "英語の品詞名",
  "etymology": "漢字の成り立ちや日本語としての語源・由来",
  "collocations": [
    "日本語のコロケーション（ロシア語訳）"
  ],
  "examples": [
    {{
      "example": "自然な日本語の例文",
      "example_translated": "例文の自然なロシア語訳"
    }},
    {{
      "example": "自然な日本語の例文",
      "example_translated": "例文の自然なロシア語訳"
    }}
  ]
}}

# 制約条件

- Web検索結果の情報を最優先する。
- Web検索結果で確認できない情報は推測しない。
- 類似語・同義語・別の単語の情報を混同しない。
- "word" は入力された "{word}" をそのまま使用する。
- "meaning" はロシア語で記載する。
- "meaning" は代表的な意味を最大3つまで記載する。
- 複数の意味は半角セミコロン ";" で区切る。
- 意味を確認できない場合は空文字 "" にする。
- "part_of_speech" は英語で記載する。
- 品詞を確認できない場合は空文字 "" にする。
- "etymology" は漢字の成り立ち、日本語としての語源・由来などを100文字以内で記載する。
- 語源を確認できない場合は空文字 "" にする。
- "collocations" は確認できたものを最大3つまで記載する。
- 各コロケーションは「日本語（ロシア語訳）」の形式にする。
- 3つ未満しか確認できない場合は、確認できたものだけ記載する。
- コロケーションを確認できない場合は [] にする。
- 存在しないコロケーションを推測して補完しない。
- "examples" は必ず2つ作成する。
- 例文には "{word}" または自然な活用形を使用する。
- 例文は自然な日本語にする。
- 2つの例文は可能なら異なる用法にする。
- "example_translated" は自然で正確なロシア語訳にする。
- 情報が確認できないフィールドは空文字 "" にする。
- JSON以外の文章を出力しない。
- Markdownのコードブロックを使用しない。

# 出力例

入力単語:

家

出力:

{{
  "word": "家",
  "meaning": "дом; семья",
  "part_of_speech": "noun",
  "etymology": "漢字は「宀」と「豕」から成り、屋根の下で豚を飼う様子を表す。日本語では住居を意味する。",
  "collocations": [
    "家を建てる（построить дом）",
    "家に帰る（вернуться домой）",
    "家族と暮らす（жить с семьёй）"
  ],
  "examples": [
    {{
      "example": "仕事が終わったら家に帰ります。",
      "example_translated": "После работы я возвращаюсь домой."
    }},
    {{
      "example": "彼は新しい家を建てました。",
      "example_translated": "Он построил новый дом."
    }}
  ]
}}
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
                search(f"{word} 意味", 5, 100),
                search(f"{word} 語源", 10, 200),
                search(f"{word} コロケーション", 10, 100),
                search(f"{word} 例文", 3, 1000),
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
