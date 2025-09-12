# テストプラン: `binaural_renderer` と `asmr_agent`

**目的:**
`asmr_agent` から `BinauralRenderer` ツールへの連携が正しく機能することを保証し、バイノーラル音声レンダリング処理の信頼性を高める。

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
│   ├── test_binaural_renderer.py
│   └── test_asmr_agent.py
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
    *   `spatial_plan_json` に含まれる可能性のあるMarkdownのコードブロック(
```json ... 
```
)が、プロンプト生成時に正しく除去されていること。
    *   最終的にプロンプトに含まれる `BinauralRenderer(...)` のツール呼び出し文字列が、全ての引数を含めて完全に正しい形式であること。

