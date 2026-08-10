import argparse
import csv
import json
import sys
from groq import Groq

# CSVに書き出す必須キーとその欠損時のデフォルト値
REQUIRED_FIELDS = {
    "word": "",
    "meaning": "",
    "part_of_speech": "",
    "etymology": "",
    "collocations": [],
    "example": "",
    "example_translated": "",
}


def build_prompt(prompt_path, word, scrape_result):
    with open(prompt_path, encoding="utf-8") as f:
        template = f.read()
    if not template.strip():
        raise ValueError(f"プロンプトファイルが空です: {prompt_path}")
    # str.format() は使わない: プロンプト内にJSON例として書かれたリテラルの { } と
    # プレースホルダの {word} が衝突し、KeyError/ValueError を引き起こすため、
    # 単純な文字列置換で {word} / {scrape_result} だけを差し替える。
    return template.replace("{word}", word).replace("{scrape_result}", scrape_result)


def call_llm(client, prompt, model="openai/gpt-oss-120b"):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content)


def normalize_data(data, word):
    """欠損キーをデフォルト値で補い、CSVに書ける形に整形する。"""
    normalized = {}
    for key, default in REQUIRED_FIELDS.items():
        value = data.get(key, default)
        if value is None:
            value = default
        normalized[key] = value

    if not normalized["word"]:
        normalized["word"] = word

    collocations = normalized["collocations"]
    if isinstance(collocations, list):
        normalized["collocations"] = "; ".join(str(c) for c in collocations)
    else:
        normalized["collocations"] = str(collocations)

    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--scrape-result", required=True)
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    args = parser.parse_args()

    try:
        prompt = build_prompt(args.prompt, args.word, args.scrape_result)
    except FileNotFoundError:
        print(f"[error] プロンプトファイルが見つかりません: {args.prompt}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[error] プロンプトの読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        client = Groq(api_key=args.api_key)
        data = call_llm(client, prompt, args.model)
    except json.JSONDecodeError as e:
        print(f"[error] LLM応答がJSONとして解析できません（word={args.word}）: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Groq側のAPIエラー（レート制限、認証エラー、タイムアウト等）を含む
        print(f"[error] Groq API呼び出しに失敗しました（word={args.word}）: {e}", file=sys.stderr)
        sys.exit(1)

    row = normalize_data(data, args.word)

    csv.writer(sys.stdout).writerow([
        row["word"],
        row["meaning"],
        row["part_of_speech"],
        row["etymology"],
        row["collocations"],
        row["example"],
        row["example_translated"],
    ])


if __name__ == "__main__":
    main()
