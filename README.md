# vocab_tool_v3

Web検索結果を利用して、日本語・ロシア語の辞書データをCSV形式で作成するツール。

## 概要

このツールは、単語リストを読み込み、Web検索で取得した情報をLLMに渡して辞書データを生成する。

対応方向：

* `ru2ja.py`：ロシア語 → 日本語
* `ja2ru.py`：日本語 → ロシア語

生成したデータはCSVに保存する。

主な取得項目：

* 単語
* 意味
* 品詞
* 語源・由来
* コロケーション
* 例文
* 例文の翻訳

## 必要環境

* Python 3.10以上推奨
* Groq APIキー
* インターネット接続

## インストール

リポジトリを取得する。

```bash
git clone https://github.com/nakamura26002002921-a11y/vocab_tool_v3.git
cd vocab_tool_v3
```

必要なライブラリをインストールする。

```bash
pip install -r requirements.txt
```

## APIキー

`run_ru2ja.py` または `run_ja2ru.py` の `API_KEYS` にGroq APIキーを設定する。

```python
API_KEYS = [
    "gsk_xxx",
    "gsk_yyy",
    "gsk_zzz",
]
```

複数のAPIキーを登録した場合、単語ごとに順番に使用する。

## 単語リスト

`words.txt` に1行1単語で入力する。

例：

```text
дом
сцена
работа
любовь
```

日本語の場合：

```text
家
学校
仕事
愛
```

空行は無視される。

## Web検索

`search.py` はDuckDuckGo検索を利用して検索結果を取得し、各ページの本文を取得する。

単体で実行する場合：

```bash
python3 search.py --word "насколько" --max-results 5 --max-chars 3000
```

主なオプション：

| オプション           | 説明              | デフォルト |
| --------------- | --------------- | ----: |
| `--word`        | 検索語             |    必須 |
| `--max-results` | 検索結果数           |    10 |
| `--max-chars`   | 1ページあたりの最大文字数   |  3000 |
| `--timeout`     | HTTP通信のタイムアウト秒数 |    10 |

### Unicodeフィルタ

`search.py` ではUnicodeコードポイントの範囲を指定して、取得した本文から特定の文字範囲以外を除去できる。

ロシア語のキリル文字を対象にする場合：

```text
0x0400 - 0x04FF
```

この機能は、ロシア語検索時に日本語や文字化けした文字などの不要な文字を減らす目的で使用する。

日本語検索では漢字・ひらがな・カタカナ・英数字などが必要になるため、基本的にはUnicodeフィルタを使用しない。

## vocab.py

`vocab.py` はGroq APIを利用してLLMを呼び出す。

単体で実行する場合：

```bash
python3 vocab.py \
  --prompt "日本語で家の意味を説明してください。" \
  --api-key "gsk_xxx"
```

`vocab.py` はLLMの結果を標準出力にJSONとして返す。

`run_ru2ja.py` と `run_ja2ru.py` から呼び出す場合は、API呼び出しを関数として実行する。

## ru2ja

ロシア語の単語から、日本語話者向けの辞書データを作成する。

例：

```bash
python3 run_ru2ja.py \
  --output result_ru2ja_1001-1200.csv \
  --words words.txt \
  --startidx 1001 \
  --endidx 1200 \
  --interval 20
```

### オプション

| オプション            | 説明       |
| ---------------- | -------- |
| `-o`, `--output` | 出力CSV    |
| `--words`        | 単語リスト    |
| `--startidx`     | 開始番号     |
| `--endidx`       | 終了番号     |
| `--interval`     | 単語間の待機秒数 |

例えば、

```bash
--startidx 1001 --endidx 1200
```

の場合、`words.txt` の1001番目から1200番目までを処理する。

## ja2ru

日本語の単語から、ロシア語話者向けの辞書データを作成する。

例：

```bash
python3 run_ja2ru.py \
  --output result_ja2ru_1-200.csv \
  --words words.txt \
  --startidx 1 \
  --endidx 200 \
  --interval 20
```

処理内容は `ru2ja` と同じだが、検索クエリと辞書データの翻訳方向が異なる。

## CSV出力

生成されるCSVには以下の項目が保存される。

```text
word
meaning
part_of_speech
etymology
collocations
example
example_translated
example
example_translated
```

コロケーションは最大3件、例文は2件保存する。

## JSON形式

LLMにはJSON形式で出力するよう指示している。

ru2jaの例：

```json
{
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
    {
      "example": "Я возвращаюсь домой после работы.",
      "example_translated": "私は仕事の後に家に帰ります。"
    },
    {
      "example": "Этот дом очень старый.",
      "example_translated": "この家はとても古いです。"
    }
  ]
}
```

## Web検索結果の扱い

辞書データの生成では、Web検索結果を優先する。

確認できない情報については推測しないようプロンプトで指定している。

特に以下を重視する。

* 類似語・同義語との混同を避ける
* 対象単語と別の単語の情報を混ぜない
* 語源は確認できた情報のみ使用する
* コロケーションは確認できたものだけ使用する
* 例文は対象単語を含める
* 翻訳は自然な文章にする

## ファイル構成

```text
vocab_tool_v3/
├── search.py
├── vocab.py
├── run_ru2ja.py
├── run_ja2ru.py
├── words.txt
├── requirements.txt
└── README.md
```

## 注意事項

Web検索結果には、Wikipedia、辞書サイト、検索結果ページ、翻訳ページなどが含まれる場合がある。

そのため、検索結果が必ずしも正確とは限らない。

特に語源や多義語については、生成されたデータを必要に応じて確認することを推奨する。

また、Groq APIには利用制限があるため、大量の単語を処理する場合は `--interval` を設定してリクエスト間隔を空ける。

例：

```bash
--interval 20
```

## ライセンス

必要に応じて設定する。
