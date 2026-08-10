import argparse
import os
import subprocess
import sys
import time

# 環境変数 VOCAB_TOOL_API_KEYS にカンマ区切りで設定すると読み込む。
# 未設定の場合はここに直接書いたキーを使う（配布時はダミー値のままでOK、各自置き換える）。
_env_keys = os.environ.get("VOCAB_TOOL_API_KEYS", "")
if _env_keys.strip():
    API_KEYS = [k.strip() for k in _env_keys.split(",") if k.strip()]
else:
    API_KEYS = [
        "gsk_xxx",
        "gsk_yyy",
        "gsk_zzz",
    ]


def search(query, results, words):
    """search.py を呼び出す。失敗時は例外を送出せず空文字を返す。"""
    try:
        proc = subprocess.run(
            ["python3", "search.py", "--word", query, "--max-results", str(results), "--max-words", str(words)],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(f"    [search timeout] query={query!r}", file=sys.stderr)
        return ""

    if proc.returncode != 0:
        print(f"    [search failed] query={query!r}: {proc.stderr.strip()}", file=sys.stderr)
        return ""

    return proc.stdout


def process_word(word, prompt, output_path, api_key):
    """1単語分の検索〜LLM整形〜CSV追記を行う。成功したら True を返す。"""
    try:
        results = "\n\n".join([
            search(f"{word} define", 5, 200),
            search(f"{word} etymology", 10, 200),
            search(f"{word} collocations", 10, 100),
            search(f"{word} reverso", 3, 200),
        ])
    except Exception as e:
        print(f"    [error] 検索処理中に予期しないエラー: {e}", file=sys.stderr)
        return False

    try:
        proc = subprocess.run(
            ["python3", "vocab.py", "--word", word, "--api-key", api_key, "--prompt", prompt, "--scrape-result", results],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(f"    [error] vocab.py がタイムアウトしました（word={word}）", file=sys.stderr)
        return False

    if proc.returncode != 0:
        print(f"    [error] vocab.py が失敗しました（word={word}）: {proc.stderr.strip()}", file=sys.stderr)
        return False

    if not proc.stdout.strip():
        print(f"    [error] vocab.py から出力がありませんでした（word={word}）", file=sys.stderr)
        return False

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(proc.stdout)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--words", default="words.txt")
    parser.add_argument("--startidx", type=int, required=True)
    parser.add_argument("--endidx", type=int, required=True)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--failed-log", default=None,
                         help="失敗した単語を書き出すファイル（未指定なら <output>.failed.txt）")
    args = parser.parse_args()

    if not os.path.exists(args.words):
        print(f"[fatal] 単語ファイルが見つかりません: {args.words}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.prompt):
        print(f"[fatal] プロンプトファイルが見つかりません: {args.prompt}", file=sys.stderr)
        sys.exit(1)

    with open(args.prompt, encoding="utf-8") as f:
        if not f.read().strip():
            print(f"[fatal] プロンプトファイルが空です: {args.prompt}", file=sys.stderr)
            sys.exit(1)

    with open(args.words, encoding="utf-8") as f:
        words = [x.strip() for x in f if x.strip()]

    if args.startidx < 1 or args.endidx > len(words) or args.startidx > args.endidx:
        print(f"[fatal] startidx/endidx が words.txt の範囲（1〜{len(words)}）と整合しません", file=sys.stderr)
        sys.exit(1)

    failed_log_path = args.failed_log or f"{args.output}.failed.txt"

    success_count = 0
    failed_words = []

    target = words[args.startidx - 1:args.endidx]
    for offset, word in enumerate(target):
        i = args.startidx + offset
        print(f"[{i}] {word}")

        api_key = API_KEYS[(i - 1) % len(API_KEYS)]
        ok = process_word(word, args.prompt, args.output, api_key)

        if ok:
            success_count += 1
        else:
            failed_words.append(word)
            print(f"    -> スキップして次の単語へ進みます", file=sys.stderr)

        if i < args.endidx:
            time.sleep(args.interval)

    print(f"\n完了: 成功 {success_count} / 失敗 {len(failed_words)} / 全体 {len(target)}")

    if failed_words:
        with open(failed_log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(failed_words) + "\n")
        print(f"失敗した単語を {failed_log_path} に書き出しました（再実行用）")


if __name__ == "__main__":
    main()
