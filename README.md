# vocab_tool_v3

単語リストを渡すと、Web検索で意味・語源・コロケーション・例文などの情報を集め、
LLM（Groq API）で整形してCSV形式の単語帳を自動生成するツールです。

英語→日本語、日本語→ロシア語、ロシア語→日本語の3方向に対応しています。

## できること

1. `words.txt` に書いた単語を1行ずつ処理
2. 単語ごとにDuckDuckGo検索＋スクレイピングで関連情報を収集
   （define / etymology / collocations / reverso の4クエリ）
3. 収集した情報をプロンプトに埋め込み、Groq API（`openai/gpt-oss-120b`）にJSON形式で整形させる
4. 結果をCSVの1行として出力ファイルに追記
5. 個別の単語で検索やLLM呼び出しが失敗しても処理を止めず、次の単語へ進む
   （失敗した単語は `<output>.failed.txt` に書き出され、あとで再実行できる）

## ファイル構成

```
vocab_tool_v3/
├── run.py            # メインスクリプト（単語リストをループ処理）
├── search.py         # Web検索＋スクレイピング
├── vocab.py          # LLMによる単語情報の整形
├── prompt/
│   ├── en2ja.txt      # 英語 → 日本語 用プロンプト
│   ├── ja2ru.txt      # 日本語 → ロシア語 用プロンプト
│   └── ru2ja.txt      # ロシア語 → 日本語 用プロンプト
└── words.txt          # 処理したい単語リスト（各自用意）
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install requests beautifulsoup4 ddgs groq
```

### 2. Groq APIキーの用意

[Groq Console](https://console.groq.com/) でAPIキーを発行してください（`gsk_...` の形式）。

複数キーをローテーションしてレート制限を回避したい場合は、カンマ区切りで環境変数に設定します。

```bash
export VOCAB_TOOL_API_KEYS="gsk_xxxxxxxx,gsk_yyyyyyyy,gsk_zzzzzzzz"
```

環境変数を設定しない場合、`run.py` 内の `API_KEYS` に直接書いたダミー値
（`gsk_xxx` など）が使われてしまい、必ず失敗するので注意してください。
自分のキーに書き換えて使うことも可能ですが、**そのままGitにコミット・pushしないよう注意してください**。

### 3. 単語リストの用意

`words.txt` に処理したい単語を1行1語で書きます。

```
apple
run
beautiful
```

## 使い方

```bash
python3 run.py \
  --words words.txt \
  --prompt prompt/en2ja.txt \
  --startidx 1 \
  --endidx 10 \
  --output vocab.csv \
  --interval 30
```

### オプション一覧

| オプション | 必須 | 説明 |
|---|---|---|
| `-o`, `--output` | ✅ | 出力するCSVファイルのパス（追記モード） |
| `--words` | | 単語リストファイル（デフォルト: `words.txt`） |
| `--startidx` | ✅ | 処理を開始する単語の位置（1始まり） |
| `--endidx` | ✅ | 処理を終了する単語の位置（この番号を含む） |
| `--interval` | | 単語ごとの処理間隔・秒（デフォルト: 30。APIのレート制限対策） |
| `--prompt` | ✅ | 使用するプロンプトファイル（`prompt/en2ja.txt` など） |
| `--failed-log` | | 失敗した単語を書き出すファイル（デフォルト: `<output>.failed.txt`） |

### 出力されるCSVの列

```
単語, 意味, 品詞, 語源, コロケーション（; 区切り）, 例文, 例文の翻訳
```

### 失敗した単語の再実行

処理中に検索エラーやLLMエラーが起きた単語は、処理をスキップして次の単語に進みます。
失敗した単語は実行終了後に `<output>.failed.txt`（例: `vocab.csv.failed.txt`）に書き出されるので、
そのリストを新しい `words.txt` として指定し、再実行してください。

```bash
python3 run.py \
  --words vocab.csv.failed.txt \
  --prompt prompt/en2ja.txt \
  --startidx 1 \
  --endidx 5 \
  --output vocab_retry.csv
```

## プロンプトファイルについて

`prompt/` 内のファイルは `{word}`（処理中の単語）と `{scrape_result}`（検索結果のテキスト）を
埋め込んだうえでLLMに渡され、決められたJSON形式（word / meaning / part_of_speech / etymology /
collocations / example / example_translated）で出力させる指示になっています。

新しい言語ペアを追加したい場合は、`prompt/xx2yy.txt` の形式でファイルを作成し、
`en2ja.txt` を参考に同じJSON構造を守ってプロンプトを書いてください。
JSONキーの構造を変える場合は `vocab.py` の `REQUIRED_FIELDS` も合わせて修正が必要です。

## 注意事項

- スクレイピング対象サイトの利用規約・robots.txtを確認のうえご利用ください。
- Groq APIの利用にはレート制限があります。単語数が多い場合は `--interval` を調整してください。
- LLMの出力（意味・語源など）は必ずしも正確とは限りません。最終的な単語帳として使う前に、
  重要な単語は目視で確認することを推奨します。
