# プロジェクト概要: ASMR-GEN

このプロジェクト「ASMR-GEN」は、与えられたシチュエーション（テキストプロンプト）から、没入感のあるバイノーラルASMR音声を自動生成するために設計されたマルチエージェントアプリケーションです。Agent Development Kit (ADK) を使用して構築されており、GoogleのGeminiモデル群を各タスクに応じて戦略的に活用しています。

## アーキテクチャ

本アプリケーションは、ADKの `SequentialAgent` を用いて5つの専門エージェントを直列に接続したパイプラインで構成されています。各エージェントは特定のタスクに特化しており、セッション状態（Session State）を通じて情報を引き継ぎながら、一連の処理を自動で実行します。

### エージェント実行順序とデータフロー

```mermaid
graph TD
    A[ユーザー入力: シチュエATION] --> B[script_agent];
    B -- "script_text (string)" --> C[tts_agent];
    C -- "wav_path (string)" --> D[jsonize_agent];
    B -- "script_text (string)" --> D;
    D -- "timed_script_json (string)" --> E[spatial_plan_agent];
    C -- "wav_path (string)" --> E;
    E -- "spatial_plan_json (string)" --> F[asmr_agent];
    C -- "wav_path (string)" --> F;
    F --> G[出力: binaural_output_path (string)];
```

| Agent | 入力 (Session Key) | 出力 (Session Key) | 説明 |
| :--- | :--- | :--- | :--- |
| `script_agent` | (ユーザー入力) | `script_text` | 状況に基づき、ひらがな中心の脚本を生成。 |
| `tts_agent` | `script_text` | `wav_path` | 脚本からモノラル音声ファイルを合成。 |
| `jsonize_agent` | `script_text`, `wav_path` | `timed_script_json` | 音声とテキストを照合し、タイムスタンプ付きのJSONを生成。 |
| `spatial_plan_agent` | `timed_script_json`, `wav_path` | `spatial_plan_json` | 没入感を高めるための空間音響プランをJSON形式で作成。 |
| `asmr_agent` | `wav_path`, `spatial_plan_json` | `binaural_output_path` | 音声に空間プランを適用し、最終的なバイノーラルASMR音声を生成。 |

---

## エージェント詳細

### 1. `script_agent`
- **役割**: ユーザーが入力したシチュエーションに基づき、ASMR用の脚本を生成します。
- **モデル**: `gemini-2.5-pro`
- **指示**: 「ASMR脚本家」として、優しく、二人称視点の語りかけるようなトーンで、約20〜40秒のひらがな中心の脚本を作成するよう指示されています。
- **ツール**: なし
- **出力**: 生成された脚本（文字列）を `script_text` としてセッション状態に保存します。

### 2. `tts_agent`
- **役割**: `script_agent`が生成した脚本を音声に変換します。
- **モデル**: `gemini-2.5-flash`
- **指示**: `synthesize_tts` ツールを呼び出し、指定されたテキストとボイス（`config.yaml`で定義）を用いて音声を合成します。
- **ツール**: `synthesize_tts` (`tools/tts.py`)
- **出力**: 生成されたモノラルWAVファイルのパスを `wav_path` としてセッション状態に保存します。

### 3. `jsonize_agent`
- **役割**: プレーンテキストの脚本とモノラル音声ファイルを分析し、各セリフに話者情報と正確なタイムスタンプを付与した構造化JSONを生成します。
- **モデル**: `gemini-2.5-pro` (マルチモーダル)
- **指示**: 「音声-脚本アライメント専門家」として、音声のタイミングを聴き取り、各セリフの話者（`main character` または `situation explainer`）を特定し、JSON形式で出力します。
- **ツール**: なし
- **出力**: タイムスタンプ付きの脚本JSON（文字列）を `timed_script_json` としてセッション状態に保存します。

### 4. `spatial_plan_agent`
- **役割**: 構造化された脚本と音声のタイミングを分析し、音の動きや響きを計画する空間演出プランを作成します。これは、本アプリケーションの没入感を実現する上で中心的な機能です。
- **モデル**: `gemini-2.5-pro` (マルチモーダル)
- **指示**: 「ASMR専門のサウンドデザイナー」として、キャラクターの動きや感情をテキストと音声から読み取り、音源の位置（方位角、仰角）、距離、リバーブ量を時系列で定義したキーフレームの配列（JSON）を生成します。
- **ツール**: なし
- **出力**: 空間演出プランのJSON（文字列）を `spatial_plan_json` としてセッション状態に保存します。

### 5. `asmr_agent`
- **役割**: モノラル音声ファイルと空間演出プランを基に、最終的なバイノーラルASMR音声をレンダリングします。
- **モデル**: `gemini-2.5-flash`
- **指示**: `BinauralRenderer` ツールを呼び出し、指定された音声ファイルと空間プランを用いてレンダリングを実行します。
- **ツール**: `BinauralRenderer` (`tools/binaural_renderer.py`)
- **出力**: 完成したバイノーラルWAVファイルのパスを `binaural_output_path` としてセッション状態に保存します。

---

## このADKコードの仕組み

このプロジェクトは、Agent Development Kit (ADK) の主要な機能を活用して構築されています。コードの全体像を理解するために、ADKの基本的な仕組みを解説します。

### 1. エージェントの定義と連携 (`agent.py`)

プロジェクトの中心となる `asmr_gen_adk/agent.py` では、`SequentialAgent` を使って、複数のエージェントを連結しています。

```python
root_agent = SequentialAgent(
    name="asmr_gen_seq",
    description="Generate a full ASMR experience from a situation.",
    sub_agents=[
        script_agent,
        tts_agent,
        jsonize_agent,
        spatial_plan_agent,
        asmr_agent,
    ],
)
```

- `SequentialAgent`: `sub_agents` に登録されたエージェントをリストの順に一つずつ実行します。
- 各エージェントは、前のエージェントの出力を引き継ぎながら、自身のタスクを実行します。

### 2. LLMエージェント (`LlmAgent`)

このプロジェクトのほとんどのエージェントは `LlmAgent` として定義されています。これは、LLMとの対話を通じてタスクを実行するエージェントです。

```python
# 例: script_agent.py
script_agent = LlmAgent(
    name="script_agent",
    model=config["models"]["script_agent"],
    description="Writes a short, single-speaker Japanese ASMR script.",
    instruction="...",
    output_key="script_text",
)
```

- `model`: 使用するGeminiモデル名を指定します (`config.yaml` から読み込み）。
- `instruction`: LLMに与える指示（プロンプト）です。静的な文字列を渡すことも、後述の動的な関数を渡すことも可能です。
- `tools`: エージェントが使用できるツールのリストです（例: `tts_agent` の `synthesize_tts`）。
- `output_key`: エージェントの実行結果（LLMの応答やツールの返り値）を、セッション状態に保存するためのキー名を指定します。

### 3. 動的な指示の構築 (`_build_instruction`)

後続のエージェントは、先行するエージェントの実行結果をプロンプトに組み込む必要があります。このために、`instruction` パラメータに `async` 関数を渡すパターンが使われています。

```python
# 例: tts_agent.py
async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    script_text = await inject_session_state("{script_text?}", readonly_ctx)
    if not script_text:
        raise ValueError("`script_text` not found in session state")
    # ... プロンプトを構築 ...
    return f"..."

tts_agent = LlmAgent(
    ...,
    instruction=_build_instruction,
    ...
)
```

- `_build_instruction`: この関数はエージェントの実行直前に呼び出されます。
- `readonly_ctx`: 現在のセッション状態への読み取り専用アクセスを提供します。
- `inject_session_state`: `"{key_name}"` のような形式で、セッション状態から値を取得し、文字列に埋め込みます。`?` を付けると、キーが存在しなくてもエラーにならず `None` が返ります。

### 4. セッション状態管理 (State Management)

エージェント間のデータ連携は、ADKのセッション状態（state）を介して行われます。

- **保存**: 各エージェントの `output_key` に指定されたキー名で、そのエージェントの実行結果が自動的にセッション状態に保存されます。
  - `script_agent` -> `state['script_text'] = "..."`
  - `tts_agent` -> `state['wav_path'] = "..."`
- **取得**: `_build_instruction` 内で `inject_session_state` を使うことで、先行するエージェントが保存した値を安全に取得できます。

この仕組みにより、エージェント同士が疎結合に保たれ、各エージェントは自身の役割に集中できます。

### 5. カスタムツールの利用

`tts_agent` や `asmr_agent` のように、LLMの能力だけでは完結しないタスク（音声合成、バイノーラルレンダリングなど）は、カスタムツールとして実装されています。

```python
# 例: tts.py
def synthesize_tts(text: str, ...) -> dict:
    # ... 音声合成処理 ...
    return {"wav_path": "..."}

# 例: tts_agent.py
tts_agent = LlmAgent(
    ...,
    tools=[synthesize_tts],  # ツールをエージェントに登録
)
```

- Python関数としてツールを定義し、`LlmAgent` の `tools` リストに渡すだけで、エージェントはLLMの判断を通じてそのツールを呼び出すことができるようになります。
- ツールの返り値（辞書形式）が、エージェントの `output_key` に従ってセッション状態に保存されます。

---

## コア技術とツール

### `tools/binaural_renderer.py`
このツールは、`asmr_agent` から呼び出され、高品質なバイノーラルレンダリングの心臓部を担います。

- **HRTF (頭部伝達関数)**: `spaudiopy` ライブラリを用いてHRTFをロードし、人間の聴覚特性に基づいたリアルな3D音像定位を実現します。
- **動的パラメータ補間**: `scipy.interpolate.interp1d` を使用し、空間プランのキーフレーム間（時間、方位角、仰角、距離、リバーブ量）を滑らかに線形補間します。
- **Input Crossfadingによるスムーズな音像移動**: 音源が移動する際に発生しがちなクリックノイズを抑制するため、レンダリングを小さなブロックに分割し、ブロック間でHRTFパラメータをクロスフェードさせる高度な手法を採用しています。これにより、非常に滑らかな音の軌跡が生成されます。
- **高品質なリバーブ**: `pedalboard` ライブラリを利用し、空間の響きを動的に生成します。距離が近づくとリバーブ量が減るなど、自然な音響変化を再現します。

### `tools/asmr_spatialize.py`
このスクリプトは、`binaural_renderer.py` とは異なるアプローチで空間音響を実現する、HRTFレスの軽量な代替実装です。現在のエージェントパイプラインでは**使用されていません**が、定電力パンニング、距離減衰、簡易EQ（LPF/HPF）などを組み合わせて「ASMRらしさ」を再現する興味深いアプローチを取っています。

### `config.yaml`
アプリケーションの動作設定を管理します。各エージェントが使用するGeminiモデル名や、TTSで使用するボイス名（プライマリとフォールバック）が定義されています。これにより、コードを変更することなく、使用するモデルや音声を柔軟に切り替えることが可能です。

## ビルドと実行

`README.md` に記載されている手順に従ってください。

1.  **インストール**: `pip install -r requirements.txt`
2.  **設定**: `.env` ファイルに `GEMINI_API_KEY` を設定。
3.  **実行**: `adk web -reload -v` または `adk run asmr_gen_adk`