# テストプラン: ASMR-GEN アプリケーション

**目的:**
ASMR-GENアプリケーションを構成する各エージェントおよびツールが、個別に、そして連携して正しく機能することを保証し、アプリケーション全体の信頼性を高める。

**使用するツール:**
*   **テストフレームワーク:** `pytest`
*   **モックライブラリ:** `unittest.mock` (Python標準ライブラリ)
*   **音声データ生成:** `numpy`

**テストファイルの構成:**
プロジェクトのルートに `tests/` ディレクトリを作成し、以下のようにファイルを配置します。

```
/home/user/asmr-gen/
├── tests/
│   ├── __init__.py
│   ├── test_script_agent.py
│   ├── test_tts_agent.py
│   ├── test_jsonize_agent.py
│   ├── test_spatial_plan_agent.py
│   ├── test_asmr_agent.py
│   └── test_binaural_renderer.py
└── ... (既存のファイル)
```

---

## 1. `binaural_renderer.py` の単体テスト

**ファイル:** `tests/test_binaural_renderer.py`

このテストの主な目的は、音声処理のコアロジックが期待通りに動作することを確認することです。

**テストケース 1: `make_asmr_audio` 関数の正常系テスト**
*   **目的:** ダミーの音声データと空間プランを指定した際に、関数がエラーなく実行され、期待される形式のバイノーラル音声データが返されることを確認する。
*   **手順:**
    1.  `numpy` を使用して、モノラルのサイン波やホワイトノイズの音声データ (`np.ndarray`) を生成する。
    2.  シンプルな空間プランをPythonのリスト/辞書として定義する (例: `[{"time": 0.0, "azimuth": 0, ...}]`)。
    3.  `make_asmr_audio` 関数をこれらのデータで呼び出す。
*   **アサーション (確認項目):**
    *   関数が `AttributeError` などの例外を発生させずに完了すること。
    *   戻り値が `(np.ndarray, int)` のタプルであること。
    *   返された音声データがステレオ (shapeが `(N, 2)`) であること。
    *   返されたサンプルレートが `TARGET_FS` (48000) であること。

**テストケース 2: `BinauralRenderer` ツールラッパーの正常系テスト**
*   **目的:** ファイルの読み書きを含めたツール全体のフローが正常に動作することを確認する。
*   **手順:**
    1.  `pytest` の `tmp_path` フィクスチャを使用して、一時的な入出力ディレクトリを作成する。
    2.  テスト用のモノラルWAVファイル (`sample.wav`) を `soundfile.write` で生成する。
    3.  テスト用の空間プランをJSON文字列として用意する。
    4.  `BinauralRenderer` 関数を、生成したWAVファイルのパス、JSON文字列、および出力先のパスを指定して呼び出す。
*   **アサーション:**
    *   指定した出力パスにWAVファイルが実際に生成されていること。
    *   関数が成功を示す辞書 (`{"binaural_output_path": "..."}`) を返すこと。
    *   生成されたWAVファイルが `soundfile.read` で読み込み可能であり、ステレオデータを含んでいること。

---

## 2. `asmr_agent.py` の単体テスト

**ファイル:** `tests/test_asmr_agent.py`

このテストの主な目的は、エージェントが受け取った状態に基づいて、LLMに対して正しい指示（プロンプト）を生成できるかを確認することです。

**テストケース 1: `_build_instruction` 関数のプロンプト生成テスト**
*   **目的:** `ReadonlyContext` から取得した情報を用いて、`BinauralRenderer` ツールを正しく呼び出すためのプロンプトが生成されることを確認する。
*   **手順:**
    1.  `unittest.mock.AsyncMock` を使用して、`ReadonlyContext` のモックを作成する。
    2.  `inject_session_state` が呼ばれた際に、テスト用の`wav_path`と`spatial_plan_json`を返すように設定する。
    3.  `_build_instruction` 関数をモックのコンテキストで `await` して呼び出す。
*   **アサーション:**
    *   返されたプロンプト文字列に、モックで設定した `wav_path` が正しく埋め込まれていること。
    *   `spatial_plan_json` に含まれる可能性のあるMarkdownのコードブロックが、プロンプト生成時に正しく除去されていること。
    *   最終的にプロンプトに含まれる `BinauralRenderer(...)` のツール呼び出し文字列が、全ての引数を含めて完全に正しい形式であること。

---

## 3. `script_agent.py` の単体テスト

**ファイル:** `tests/test_script_agent.py`

**目的:**
ユーザーからの入力に基づき、LLMに対して脚本生成を指示するプロンプトが正しく構築されることを確認する。

**テストケース 1: プロンプト生成テスト**
*   **目的:** `LlmAgent` に渡される `instruction` 文字列が、期待される基本プロンプトを含んでいることを確認する。
*   **手順:**
    1.  `script_agent` オブジェクトをインポートする。
    2.  `script_agent.instruction` 属性にアクセスする。
*   **アサーション:**
    *   `instruction` が文字列であること。
    *   プロンプトに「ASMR scriptwriter」「based on the situation given」などのキーワードが含まれていることを確認する。
    *   ユーザー入力が追記されることを想定した基本構造になっていることを確認する。

---

## 4. `tts_agent.py` の単体テスト

**ファイル:** `tests/test_tts_agent.py`

**目的:**
`script_agent` が生成した脚本テキストをコンテキストから受け取り、TTSツールを呼び出すためのプロンプトを正しく生成できるかを確認する。

**テストケース 1: `_build_instruction` 関数の正常系テスト**
*   **目的:** `ReadonlyContext` から脚本テキストを正しく取得し、`synthesize_tts` ツールを呼び出すプロンプトを生成することを確認する。
*   **手順:**
    1.  `unittest.mock.AsyncMock` を使用して `ReadonlyContext` のモックを作成する。
    2.  `inject_session_state` が `"{script_text?}"` というキーで呼ばれた際に、テスト用の脚本テキストを返すように設定する。
    3.  `_build_instruction` 関数をモックのコンテキストで呼び出す。
*   **アサーション:**
    *   返されたプロンプトに、モックで設定した脚本テキストが正しく埋め込まれていること。
    *   プロンプトに `synthesize_tts(text=..., voice_name='Kore')` というツール呼び出しの指示が含まれていること。
    *   失敗した場合のリトライ指示 (`voice_name='Puck'`) が含まれていること。

**テストケース 2: `_build_instruction` 関数の異常系テスト（`script_text` がない場合）**
*   **目的:** コンテキストに `script_text` が存在しない場合に、`ValueError` が発生することを確認する。
*   **手順:**
    1.  `ReadonlyContext` のモックを作成し、`inject_session_state` が `None` を返すように設定する。
    2.  `pytest.raises(ValueError)` を使用して、`_build_instruction` を呼び出す。
*   **アサーション:**
    *   `ValueError` が正しく送出されること。

---

## 5. `jsonize_agent.py` の単体テスト

**ファイル:** `tests/test_jsonize_agent.py`

**目的:**
音声ファイルパスと脚本テキストをコンテキストから受け取り、タイムスタンプ付きJSONを生成するためのプロンプトを正しく構築できるかを確認する。

**テストケース 1: `_build_instruction` 関数のプロンプト生成テスト**
*   **目的:** `ReadonlyContext` から `wav_path` と `script_text` を取得し、JSON生成用のプロンプトを正しく構築することを確認する。
*   **手順:**
    1.  `ReadonlyContext` のモックを作成する。
    2.  `inject_session_state` が呼ばれた際に、テスト用の `wav_path` と `script_text` を返すように設定する。
    3.  `_build_instruction` 関数をモックのコンテキストで呼び出す。
*   **アサーション:**
    *   返されたプロンプトに、モックで設定した `wav_path` が正しく埋め込まれていること。
    *   返されたプロンプトに、モックで設定した `script_text` が正しく埋め込まれていること。
    *   プロンプトにJSONの出力形式を指示するキーワード（例: `scene_elements`, `start_time`）が含まれていること。

---

## 6. `spatial_plan_agent.py` の単体テスト

**ファイル:** `tests/test_spatial_plan_agent.py`

**目的:**
タイムスタンプ付きのJSON脚本と音声ファイルパスをコンテキストから受け取り、空間音響プランを生成するためのプロンプトを正しく構築できるかを確認する。

**テストケース 1: `_build_instruction` 関数のプロンプト生成テスト**
*   **目的:** `ReadonlyContext` から `timed_script_json` と `wav_path` を取得し、空間プラン生成用のプロンプトを正しく構築することを確認する。
*   **手順:**
    1.  `ReadonlyContext` のモックを作成する。
    2.  `inject_session_state` が呼ばれた際に、テスト用の `timed_script_json`（JSON文字列）と `wav_path` を返すように設定する。
    3.  `_build_instruction` 関数をモックのコンテキストで呼び出す。
*   **アサーション:**
    *   返されたプロンプトに、モックで設定した `timed_script_json` が正しく埋め込まれていること。
    *   返されたプロンプトに、モックで設定した `wav_path` が正しく埋め込まれていること。
    *   プロンプトに空間プランの出力形式を指示するキーワード（例: `keyframes`, `azimuth`, `elevation`）が含まれていること。

---

## 7. 結合テスト

**ファイル:** `tests/test_sequential_agent.py`

**目的:**
`SequentialAgent` で連結されたエージェント群が、最初のユーザー入力から最終的なバイノーラル音声ファイル生成まで、一連のデータフローとして正しく連携して動作することを検証する。外部API（LLM, TTS）への実際のアクセスはモック化し、エージェント間のデータの受け渡しと状態遷移に焦点を当てる。

**テストケース 1: `SequentialAgent` のE2E（エンドツーエンド）フローテスト**
*   **目的:** ユーザーの初期入力から始まり、全てのエージェントが順次実行され、最終的にバイノーラル音声ファイルが生成される（という想定の）パスが出力されることを確認する。
*   **手順:**
    1.  `unittest.mock.patch` を使用して、各エージェントが内部で呼び出す `LlmAgent` の `execute` メソッドおよび、`tts_agent` と `asmr_agent` が使用するツール（`synthesize_tts`, `BinauralRenderer`）をモックする。
    2.  各モックが、後続のエージェントが必要とするデータを模した、期待される戻り値を返すように設定する。
        *   `script_agent` のモック: 固定の脚本テキストを返す。
        *   `tts_agent` のツールのモック: ダミーのWAVファイルパスを返す。
        *   `jsonize_agent` のモック: 固定のタイムスタンプ付きJSONを返す。
        *   `spatial_plan_agent` のモック: 固定の空間プランJSONを返す。
        *   `asmr_agent` のツールのモック: ダミーのバイノーラルWAVファイルパスを返す。
    3.  `asmr_gen_adk.agent.asmr_gen_app` (`SequentialAgent`) の `execute` メソッドを、テスト用の初期入力（例: "ささやき声で羊を数える"）で呼び出す。
*   **アサーション:**
    *   `SequentialAgent` の `execute` が例外を発生させずに完了すること。
    *   最終的な結果として、`asmr_agent` のツールモックが返したバイノーラルWAVファイルパスを含む辞書が返されること。
    *   各エージェントのモックが、期待される順序で1回ずつ呼び出されていることを確認する (`mock.assert_called_once()` などを使用)。
    *   後続のエージェントが、先行するエージェントの出力（モックの戻り値）を正しく受け取って処理を開始していることを、モックの呼び出し引数を検証することで確認する。

