import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime

from groq import Groq
from groq import APIError, APIConnectionError, APITimeoutError, RateLimitError

API_KEYS = [
    "gsk_xxx",
    "gsk_yyy",
    "gsk_zzz",
]

# 中の { } はJSON例なので .format() に壊されないよう {{ }} でエスケープしている。
# 差し込むのは {word} と {results} の2箇所のみ。
PROMPT = """
ロシア語の単語「{word}」について、以下のWeb検索結果を参考にして情報を整理してください。

【Web検索結果】
{results}

以下のJSON形式で出力してください。

{{
  "word": "ロシア語の単語",
  "meaning": "日本語訳",
  "part_of_speech": "品詞",
  "etymology": "語源",
  "collocations": [
    "代表的なコロケーション1",
    "代表的なコロケーション2",
    "代表的なコロケーション3"
  ],
  "examples": [
    {{
      "example": "自然なロシア語の例文1",
      "example_translated": "例文1の日本語訳"
    }},
    {{
      "example": "自然なロシア語の例文2",
      "example_translated": "例文2の日本語訳"
    }}
  ]
}}

ルール:
- Web検索結果の情報を優先する
- 情報がない場合は無理に推測しない
- 語源は簡潔にする
- 品詞は英語で記載する
- コロケーションは3つ
- 例文は2つ、それぞれ用法が異なる自然なロシア語にする
- JSONのみ出力する
"""

REQUIRED_KEYS = [
    "word", "meaning", "part_of_speech", "etymology",
    "collocations", "examples",
]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr)


def write_failure_log(log_path, idx, word, reason):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()}\t{idx}\t{word}\t{reason}\n")


def search(query, max_results, max_words, retries=2, backoff=3):
    """search.py をサブプロセスで呼び出す。失敗時は指定回数までリトライし、
    それでもダメなら例外を送出する(呼び出し元で単語ごとスキップ判定するため)。
    """
    last_error = None
    for attempt in range(1, retries + 2):
        try:
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
                timeout=120,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            last_error = e
            if attempt <= retries:
                wait = backoff * attempt
                log(f"  [search retry {attempt}/{retries}] query={query!r}: {e} -> {wait}s待機")
                time.sleep(wait)
                continue
            raise RuntimeError(f"search.py failed for query={query!r}: {last_error}") from last_error


def call_groq(client, prompt, retries=3, backoff=5):
    """Groq APIを呼び出す。接続エラー/レートリミット/タイムアウトはリトライし、
    それでもダメなら例外を送出する。
    """
    last_error = None
    for attempt in range(1, retries + 2):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            last_error = e
            wait = backoff * attempt * 2  # レートリミットは長めに待つ
        except (APIConnectionError, APITimeoutError) as e:
            last_error = e
            wait = backoff * attempt
        except APIError as e:
            # 4xx系(認証エラー等)はリトライしても直らないことが多いが、
            # 一過性の場合もあるため一応既定回数はリトライする
            last_error = e
            wait = backoff * attempt

        if attempt <= retries:
            log(f"  [groq retry {attempt}/{retries}] {last_error} -> {wait}s待機")
            time.sleep(wait)
        else:
            raise RuntimeError(f"Groq API call failed: {last_error}") from last_error


def parse_and_validate(raw_json):
    """Groqの応答をJSONとしてパースし、必須キーの存在を検証する。"""
    data = json.loads(raw_json)  # json.JSONDecodeError は呼び出し元でキャッチ
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"応答JSONに必須キーが不足: {missing}")
    if not isinstance(data["collocations"], list):
        raise ValueError("collocationsがリストではありません")
    if not isinstance(data["examples"], list) or len(data["examples"]) != 2:
        raise ValueError("examplesは2件のリストである必要があります")
    for ex in data["examples"]:
        if "example" not in ex or "example_translated" not in ex:
            raise ValueError("examplesの各要素にexample/example_translatedが必要です")
    return data


def process_word(client, word):
    """1単語分の検索〜Groq呼び出し〜パースまでを行う。
    どこかで失敗したら例外を送出する(呼び出し元でスキップ・ログ記録)。
    """
    results = "\n\n".join([
        search(f"{word} значение", 5, 1000),
        search(f"{word} этимология", 10, 1000),
        search(f"{word} сочетаемость", 10, 100),
        search(f"{word} reverso", 3, 1000),
    ])

    prompt = PROMPT.format(word=word, results=results)

    raw = call_groq(client, prompt)

    try:
        data = parse_and_validate(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Groq応答のパースに失敗: {e} / raw={raw[:200]!r}") from e

    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--words", default="words.txt")
    parser.add_argument("--startidx", type=int, required=True)
    parser.add_argument("--endidx", type=int, required=True)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument(
        "--fail-log", default="failed_words.tsv",
        help="スキップした単語を記録するログファイル",
    )
    args = parser.parse_args()

    with open(args.words, encoding="utf-8") as f:
        words = [x.strip() for x in f if x.strip()]

    total = args.endidx - args.startidx + 1
    ok_count = 0
    fail_count = 0

    for i, word in enumerate(
        words[args.startidx - 1:args.endidx],
        args.startidx,
    ):
        log(f"[{i}] {word} を処理中...")

        client = Groq(api_key=API_KEYS[(i - 1) % len(API_KEYS)])

        try:
            data = process_word(client, word)
        except Exception as e:
            fail_count += 1
            log(f"  [FAIL] {word}: {e} -> スキップして次の単語へ")
            write_failure_log(args.fail_log, i, word, str(e))
            if i < args.endidx:
                time.sleep(args.interval)
            continue

        try:
            with open(args.output, "a", encoding="utf-8", newline="") as f:
                ex1, ex2 = data["examples"]
                csv.writer(f).writerow([
                    data["word"],
                    data["meaning"],
                    data["part_of_speech"],
                    data["etymology"],
                    "; ".join(data["collocations"]),
                    ex1["example"],
                    ex1["example_translated"],
                    ex2["example"],
                    ex2["example_translated"],
                ])
        except OSError as e:
            # 出力できなければスキップ扱いにはできない(データはあるのに消えるため)
            # ログに残して処理は継続する
            fail_count += 1
            log(f"  [FAIL] {word}: CSV書き込み失敗: {e}")
            write_failure_log(args.fail_log, i, word, f"csv write error: {e}")
            if i < args.endidx:
                time.sleep(args.interval)
            continue

        ok_count += 1
        log(f"  [OK] {word}")

        if i < args.endidx:
            time.sleep(args.interval)

    log(f"完了: 成功 {ok_count}/{total}, 失敗 {fail_count}/{total}")
    if fail_count:
        log(f"失敗した単語は {args.fail_log} を参照してください")


if __name__ == "__main__":
    main()
