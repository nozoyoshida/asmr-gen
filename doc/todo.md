# ASMR-GEN 開発ToDoリスト

## P0: 最優先タスク（アプリケーションの正常化）

- [ ] **`binaural_renderer`ツールの修正**
    - **内容**: `asmr_agent` と `BinauralRenderer` ツールの間のインターフェースの不整合を解消する。
    - **ファイル**: `asmr_gen_adk/tools/binaural_renderer.py`
    - **具体的な作業**:
        1. `make_asmr_audio` 関数から、現在使用していない `script_json` 引数を削除する。
        2. `BinauralRenderer` ツール関数から、`script_json` に関連する処理を削除する。
    - **ゴール**: `asmr_agent` が渡すデータ（モノラル音声と空間プラン）だけで、バイノーラル音声が正しく生成されるようにする。

## P1: 品質と安定性の向上

- [ ] **エラーハンドリングの強化**
    - **内容**: 各エージェントのAPI呼び出しやファイルI/Oでエラーが発生した場合の、リトライやフォールバック処理を実装する。
    - **対象**: 全てのエージェント (`script_agent`, `tts_agent`, `jsonize_agent`, `spatial_plan_agent`, `asmr_agent`)

- [ ] **JSONバリデーションの導入**
    - **内容**: `jsonize_agent` と `spatial_plan_agent` が生成するJSONの形式が正しいか検証する処理を追加する。不正な場合はエラーハンドリングを行う。
    - **対象**: `jsonize_agent`, `spatial_plan_agent`

- [ ] **出力管理の改善**
    - **内容**: 生成される全ての中間ファイルと最終成果物を、実行ごとにタイムスタンプ付きのユニークなディレクトリに保存するように変更する。
    - **対象**: `tts_agent`, `jsonize_agent`, `spatial_plan_agent`, `asmr_agent`

## P2: メンテナンス性と拡張性の向上

- [ ] **設定の外部化**
    - **内容**: コード内にハードコーディングされているモデル名 (`gemini-2.5-pro` 等) やTTSのボイス名 (`Kore` 等) を、設定ファイル（例: `config.yaml`）に分離する。
    - **対象**: `script_agent`, `tts_agent`, `jsonize_agent`, `spatial_plan_agent`

- [ ] **テストコードの導入**
    - **内容**: 各エージェントの単体テストと、`SequentialAgent` の全体的な動作を検証する結合テストを作成する。
    - **ゴール**: 将来の機能追加やリファクタリングを安全に行えるようにする。

---
