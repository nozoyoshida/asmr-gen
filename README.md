# Gemini API TTS

Google の Gemini API を使用してテキストを音声に変換するシンプルなPythonプログラムです。

## 機能

- テキストを自然な音声に変換
- 30種類の音声から選択可能
- MP4形式での高品質音声出力
- コマンドライン & インタラクティブ操作
- 24言語対応（自動言語検出）

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` ファイルを作成し、Gemini API キーを設定してください。

```bash
cp .env.example .env
```

`.env` ファイルを編集:
```bash
GEMINI_API_KEY=your_actual_api_key_here
DEFAULT_VOICE=Kore
OUTPUT_DIR=./output
```

### 3. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. API キーを生成
3. `.env` ファイルに設定

## 使用方法

### 基本的な使用法

```bash
# コマンドライン引数でテキスト指定
python main.py "こんにちは、世界！"

# インタラクティブモード
python main.py

# 音声を指定
python main.py "Hello World" --voice Puck

# 出力ファイル名を指定
python main.py "テストメッセージ" --output test_message
```

### コマンドオプション

```bash
python main.py [TEXT] [OPTIONS]

引数:
  TEXT                  変換するテキスト（省略時はインタラクティブ入力）

オプション:
  -v, --voice TEXT      使用する音声名 (デフォルト: Kore)
  -o, --output TEXT     出力ファイル名 (拡張子なし)
  --list-voices         利用可能な音声一覧を表示
  --help               ヘルプメッセージを表示
```

### 利用可能な音声

```bash
python main.py --list-voices
```

主要な音声:
- **Kore**: 女性の声
- **Puck**: 男性の声
- **Charon**: 深みのある男性の声
- **Fenrir**: 力強い男性の声
- **Aoede**: 優雅な女性の声
- その他25種類

## 使用例

### 1. 基本的なテキスト変換

```bash
python main.py "おはようございます。今日も良い一日をお過ごしください。"
```

### 2. 英語テキストを男性の声で変換

```bash
python main.py "Good morning! Have a wonderful day." --voice Puck
```

### 3. カスタムファイル名で保存

```bash
python main.py "重要なお知らせです" --output announcement --voice Charon
```

### 4. インタラクティブモード

```bash
python main.py
# プロンプトでテキストを入力
```

## 出力

- 音声ファイルは `output/` ディレクトリに保存されます
- ファイル形式: MP4 (高品質音声)
- ファイル名: 指定しない場合は `speech_YYYYMMDD_HHMMSS.mp4`

## エラー対処

### API キー関連

```
Error: GEMINI_API_KEY environment variable is required.
```
→ `.env` ファイルにAPI キーを設定してください

### 音声選択エラー

```
Error: Invalid voice 'VoiceName'.
```
→ `--list-voices` で利用可能な音声を確認してください

### 接続エラー

```
Failed to generate speech: [error details]
```
→ インターネット接続と API キーの有効性を確認してください

## 制限事項

- 入力: テキストのみ（32,000トークン制限）
- 出力: 音声のみ
- レート制限: Gemini API の制限に従います
- 対応言語: 24言語（自動検出）

## トラブルシューティング

### 1. モジュールが見つからない

```bash
pip install -r requirements.txt
```

### 2. 権限エラー

```bash
chmod +x main.py
```

### 3. 出力ディレクトリが作成されない

```bash
mkdir -p output
```

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 貢献

バグ報告や機能追加の提案は Issues でお知らせください。

---

**注意**: このツールを使用するには有効な Gemini API キーが必要です。API の使用には料金が発生する場合があります。