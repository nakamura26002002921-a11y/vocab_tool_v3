import argparse
import csv
import json
import os
import subprocess
import sys
import time

API_KEYS = [
    "gsk_xxx",
    "gsk_yyy",
    "gsk_zzz",
]


PROMPT = """
Ты помогаешь носителям японского языка изучать русский язык.

Целевое японское слово: «{word}»

Ниже приведены результаты веб-поиска. Используй их для составления
словарной статьи о слове «{word}».

【Результаты веб-поиска】
{results}

Выведи результат строго в следующем формате JSON:

{{
  "word": "{word}",
  "reading": "чтение японского слова",
  "meaning": "значение слова на русском языке",
  "part_of_speech": "часть речи на английском языке",
  "etymology": "краткое происхождение слова",
  "collocations": [
    "типичное словосочетание 1",
    "типичное словосочетание 2",
    "типичное словосочетание 3"
  ],
  "examples": [
    {{
      "example": "естественное предложение на русском языке",
      "example_translated": "перевод предложения на японский язык"
    }},
    {{
      "example": "естественное предложение на русском языке",
      "example_translated": "перевод предложения на японский язык"
    }}
  ]
}}

Правила:

- В первую очередь используй информацию из результатов веб-поиска.
- Не выдумывай информацию, которой нет в результатах поиска.
- Если необходимой информации нет, оставляй соответствующее поле пустым.
- Поле "word" должно содержать исходное японское слово «{word}».
- "reading" должно содержать чтение японского слова хираганой.
- "meaning" должно содержать значение слова на русском языке.
- "part_of_speech" указывай только на английском языке.
- "etymology" описывай кратко.
- Указывай не более 3 типичных коллокаций.
- Если найдено меньше 3 подходящих коллокаций, указывай только найденные.
- Если подходящих коллокаций нет, используй пустой массив [].
- Не придумывай коллокации только для того, чтобы заполнить три позиции.
- Должно быть ровно 2 примера.
- Примеры должны быть естественными и содержать соответствующее русское
  слово или его естественную грамматическую форму.
- "example_translated" должен содержать перевод примера на японский язык.
- Выводи только JSON без пояснений и без markdown-разметки.
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

        results = "\n\n".join([
            search(f"{word} 意味", 5, 100),
            search(f"{word} 語源", 10, 200),
            search(f"{word} コロケーション", 10, 100),
            search(f"{word} 例文", 3, 1000),
        ])

        try:
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
                    data.get("reading", ""),
                    data.get("meaning", ""),
                    data.get("part_of_speech", ""),
                    data.get("etymology", ""),
                    "; ".join(collocations),
                    examples[0].get("example", "") if len(examples) > 0 else "",
                    examples[0].get("example_translated", "") if len(examples) > 0 else "",
                    examples[1].get("example", "") if len(examples) > 1 else "",
                    examples[1].get("example_translated", "") if len(examples) > 1 else "",
                ])

        except Exception as e:
            print(f"[{i}] ERROR: {e}", file=sys.stderr)

        if i < args.endidx:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
