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

# 出力形式

以下のJSON形式で出力してください。

{{
  "word": "{word}",
  "reading": "ひらがなでの読み",
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

Web検索結果を最優先する。確認できない情報は推測しない。類似語・同義語・別語の情報を混同しない。対象単語と直接関係しない情報を使用しない。
「word」は入力値「{word}」をそのまま使用する。「word」には読みを付けない。表記を変更したり、漢字をひらがなに変換したりしない。
「reading」は「word」の自然な日本語の読みを、ひらがなだけで記載する。カタカナ・漢字・ローマ字は使用しない。確認できない場合は「""」とする。
「meaning」は日本語の意味をロシア語で記載する。代表的な意味を最大3つまで記載し、複数の意味は「;」で区切る。確認できない場合は「""」とする。
「part_of_speech」は英語の品詞名で記載する。確認できない場合は「""」とする。
「etymology」は漢字の成り立ち、日本語としての語源・由来などをロシア語で記載する。100文字以内を目安とする。Web検索結果で確認できない情報は推測しない。漢字の成り立ちや語源に諸説ある場合は、確認できた説だけを記載する。確認できない場合は「""」とする。「etymology」は必ずロシア語で記載する。
「collocations」はWeb検索で確認できた自然な日本語のコロケーションを最大3つ記載する。「日本語（ロシア語訳）」の形式とする。日本語部分に漢字が含まれる場合は、すべての漢字の直後に「（ひらがな）」形式で読みを付ける。例えば「家（いえ）を建（た）てる（построить дом）」のように記載する。3つ未満の場合は、確認できたものだけを記載する。存在しないコロケーションを推測して補完しない。確認できない場合は「[]」とする。
「examples」は必ず2つ作成する。「{word}」またはその自然な活用形を含む、日本語として自然な例文を作成する。可能であれば異なる用法の例文を2つ作成する。実際の日本語として不自然な例文を作成しない。日本語の例文に漢字が含まれる場合は、すべての漢字の直後に「（ひらがな）」形式で読みを付ける。例えば「仕事（しごと）が終（お）わったら家（いえ）に帰（かえ）ります。」のように記載する。
「example_translated」は対応する日本語例文の自然で正確なロシア語訳とする。意味を省略したり、不自然な直訳にしたりしない。「example_translated」はロシア語で記載し、ロシア語の文章には日本語のふりがなを付けない。
日本語を含む「collocations」「examples」などのフィールドでは、漢字の読みを必ずひらがなで付ける。送り仮名には読みを付けない。すでにひらがな・カタカナ・ローマ字で書かれている部分には読みを付けない。「word」だけは例外として、入力値をそのまま使用する。「reading」は読みだけをひらがなで記載する。
Web検索結果で確認できない情報を一般知識だけで補完しない。対象単語と別の単語についての情報を混同しない。特に語源や漢字の成り立ちは慎重に扱い、確証がない場合は推測しない。情報が確認できない場合は、該当フィールドを「""」または「[]」とする。
指定されたJSON形式を厳密に守る。JSON以外の文章を出力しない。Markdownコードブロックを使用しない。JSONのキー名を変更しない。


# 出力例

入力単語:

家

出力:

{{
  "word": "家",
  "reading": "いえ",
  "meaning": "дом; семья",
  "part_of_speech": "noun",
  "etymology": "Иероглиф 家 состоит из 宀 («крыша») и 豕 («свинья») и первоначально изображал свинью под крышей.",
  "collocations": [
    "家（いえ）を建（た）てる（построить дом）",
    "家（いえ）に帰（かえ）る（вернуться домой）",
    "家族（かぞく）と暮（く）らす（жить с семьёй）"
  ],
  "examples": [
    {{
      "example": "仕事（しごと）が終（お）わったら家（いえ）に帰（かえ）ります。",
      "example_translated": "После работы я возвращаюсь домой."
    }},
    {{
      "example": "彼（かれ）は新（あたら）しい家（いえ）を建（た）てました。",
      "example_translated": "Он построил новый дом."
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
                search(f"{word} 意味", 2, 600),
                search(f"{word} 由来", 2, 600)
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
