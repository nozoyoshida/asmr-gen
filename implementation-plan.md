# Gemini API TTS プログラム実装計画

## プロジェクト概要

Google の Gemini API を使用してテキストを音声に変換するシンプルなPythonプログラムを実装します。

## 目的

- テキスト入力を自然な音声に変換
- 複数の音声オプションを提供
- 使いやすいコマンドラインインターフェース
- 高品質な音声ファイル（MP4形式）を出力

## 技術仕様

### 使用API
- **Gemini 2.5 Flash Preview TTS** または **Gemini 2.5 Pro Preview TTS**
- Google Generative AI Python SDK

### 音声出力形式
- **MP4形式** での音声ファイル出力
- 高品質な音声エンコーディング

### 対応言語
- 24言語対応（日本語含む）
- 自動言語検出機能

## ファイル構成

```
/asmr-gen/
├── implementation-plan.md    # このファイル（実装計画書）
├── main.py                   # メインTTSプログラム
├── requirements.txt          # Python依存関係
├── .env.example             # 環境変数設定例
├── README.md                # 使用方法とドキュメント
└── output/                  # 生成された音声ファイルの保存先
```

## 実装詳細

### 1. main.py の主要機能

#### 基本機能
- Gemini API クライアントの初期化
- テキスト入力の受付（CLI引数またはインタラクティブ）
- 音声生成リクエストの送信
- MP4形式での音声ファイル保存

#### 音声オプション
利用可能な音声（30種類から選択可能）:
- **Kore**: 女性の声
- **Puck**: 男性の声  
- **Charon**: 深みのある男性の声
- **Fenrir**: 力強い男性の声
- **Aoede**: 優雅な女性の声
- その他25種類

#### エラーハンドリング
- API接続エラー
- 認証エラー
- テキスト長制限エラー
- ファイル保存エラー

### 2. 設定と環境変数

#### 必要な環境変数
```bash
GEMINI_API_KEY=your_api_key_here
DEFAULT_VOICE=Kore
OUTPUT_DIR=./output
```

#### 設定オプション
- 音声選択
- 出力ファイル名
- 出力ディレクトリ
- 音声品質設定

### 3. 依存関係（requirements.txt）

```txt
google-generativeai>=0.3.0
python-dotenv>=1.0.0
click>=8.0.0
```

## 使用方法

### 基本使用法

```bash
# コマンドライン引数でテキスト指定
python main.py "こんにちは、世界！"

# インタラクティブモード
python main.py

# 音声指定
python main.py "Hello World" --voice Puck

# 出力ファイル名指定
python main.py "テストメッセージ" --output test_message.mp4
```

### 詳細オプション

```bash
python main.py [TEXT] [OPTIONS]

Options:
  --voice TEXT        音声名 (default: Kore)
  --output TEXT       出力ファイル名 (default: 自動生成)
  --list-voices       利用可能な音声一覧を表示
  --help             ヘルプメッセージを表示
```

## API仕様

### リクエスト例

```python
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=input_text,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name='Kore',
                )
            )
        ),
    )
)
```

### レスポンス処理

```python
# 音声データの取得
audio_data = response.candidates[0].content.parts[0].inline_data.data

# MP4ファイルとして保存
with open(output_file, 'wb') as f:
    f.write(audio_data)
```

## 制限事項

- **入力**: テキストのみ（32kトークン制限）
- **出力**: 音声のみ
- **レート制限**: Gemini APIの制限に従う
- **ファイルサイズ**: 生成される音声ファイルのサイズ制限

## セキュリティ考慮事項

- API キーの安全な管理（環境変数使用）
- 入力テキストの適切な検証
- 出力ファイルの適切な権限設定

## 今後の拡張可能性

- 複数話者対応（マルチスピーカーTTS）
- 音声の感情・トーン制御
- バッチ処理機能
- GUI インターフェース
- 音声プレビュー機能

## 開発・テスト手順

1. 環境設定（Python 3.8+）
2. 依存関係インストール
3. Gemini API キー設定
4. 基本機能実装
5. テスト実行
6. エラーハンドリング実装
7. ドキュメント作成

この実装計画に基づいて、実用的でシンプルなGemini API TTSプログラムを開発します。