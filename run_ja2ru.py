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

PROMPT = """
Ты помогаешь носителям русского языка изучать японский язык.

Целевое слово: «{word}»

Ниже приведены результаты веб-поиска по этому слову. Используй их, чтобы
составить словарную статью СТРОГО про слово «{word}» и никакое другое.

【Результаты веб-поиска】
{results}

ВАЖНО — во избежание путаницы со словами:
- Составляй статью ТОЛЬКО для слова «{word}». Если в результатах поиска
  встречаются другие японские слова (омонимы, похожие слова, другие
  значения кандзи), НЕ используй их значение, чтения или примеры.
- Если результаты поиска не относятся к слову «{word}» или релевантной
  информации недостаточно, не выдумывай данные — используй только то,
  что действительно подтверждено результатами поиска, и оставляй поле
  пустым ("") там, где данных нет, а не заменяй его похожим словом.
- Поле "word" должно содержать ТОЧНО «{word}», без изменений.
- Все примеры предложений должны реально содержать слово «{word}»
  (а не однокоренное или похожее слово).

Выведи результат СТРОГО в следующем формате JSON (все значения на
русском языке, кроме поля "word" и текста примеров на японском):

{{
  "word": "{word}",
  "reading": "чтение хираганой",
  "meaning": "значение на русском",
  "part_of_speech": "часть речи (на английском)",
  "etymology": "происхождение слова (кратко)",
  "collocations": [
    "типичное словосочетание 1",
    "типичное словосочетание 2",
    "типичное словосочетание 3"
  ],
  "examples": [
    {{
      "example": "естественное предложение на японском 1",
      "example_translated": "перевод примера 1 на русский"
    }},
    {{
      "example": "естественное предложение на японском 2",
      "example_translated": "перевод примера 2 на русский"
    }}
  ]
}}

Правила:
- Приоритет отдавай информации из результатов веб-поиска
- Не додумывай информацию, если её нет в результатах поиска
- Происхождение слова описывай кратко
- Часть речи указывай на английском
- Словосочетаний должно быть ровно 3
- Примеров должно быть ровно 2, с разным употреблением слова, оба
  должны реально содержать слово «{word}»
- Поле "reading" обязательно, если в слове есть кандзи; если слово
  состоит только из хираганы/катаканы — укажи само слово
- Выводи ТОЛЬКО JSON, без пояснений и без markdown-разметки
"""

REQUIRED_KEYS = [
    "word", "reading", "meaning", "part_of_speech", "etymology",
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
            last_error = e
            wait = backoff * attempt

        if attempt <= retries:
            log(f"  [groq retry {attempt}/{retries}] {last_error} -> {wait}s待機")
            time.sleep(wait)
        else:
            raise RuntimeError(f"Groq API call failed: {last_error}") from last_error


def parse_and_validate(raw_json, expected_word):
    data = json.loads(raw_json)  # json.JSONDecodeError は呼び出し元でキャッチ
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"応答JSONに必須キーが不足: {missing}")
    if data["word"] != expected_word:
        raise ValueError(
            f"単語の不一致を検出(ハルシネーションの疑い): "
            f"期待={expected_word!r}, 応答={data['word']!r}"
        )
    if not isinstance(data["collocations"], list):
        raise ValueError("collocationsがリストではありません")
    if not isinstance(data["examples"], list) or len(data["examples"]) != 2:
        raise ValueError("examplesは2件のリストである必要があります")
    for ex in data["examples"]:
        if "example" not in ex or "example_translated" not in ex:
            raise ValueError("examplesの各要素にexample/example_translatedが必要です")
        if expected_word not in ex["example"]:
            raise ValueError(
                f"例文に対象単語が含まれていません(ハルシネーションの疑い): "
                f"word={expected_word!r}, example={ex['example']!r}"
            )
    return data


def process_word(client, word):
    results = "\n\n".join([
        search(f"{word} 意味", 5, 100),
        search(f"{word} 語源", 10, 200),
        search(f"{word} コロケーション", 10, 100),
        search(f"{word} 例文", 3, 1000),
    ])

    prompt = PROMPT.format(word=word, results=results)

    raw = call_groq(client, prompt)

    try:
        data = parse_and_validate(raw, word)
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
                    data["reading"],
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
