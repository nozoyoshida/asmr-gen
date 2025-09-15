# ASMR-GEN 開発ToDoリスト

## これから着手

### P0: ASMR品質の向上

- [ ] **空間音響の改善による高品質なASMR体験の実現**
    - **内容**: 現状のASMR音声はリバーブが強く、音の定位や移動がシチュ-ションに合っていないため、よりリアルで没入感のある体験を提供できていない。`spatial_plan_agent` と `asmr_agent` のロジックを改善し、高品質なバイノーラル音声を生成する。
    - **課題**:
        - リバーブが過剰で、洞窟内にいるような不自然な反響音になっている。
        - 脚本のシチュエーション（例: 「右耳元で囁く」）と実際の音響（音の定位、動き）が一致していない。
    - **具体的な作業**:
        1. [x] 現状のASMR音声生成の仕組み（`spatial_plan_agent` と `asmr_agent` の連携、`binaural_renderer` の処理）をドキュメントにまとめる。 (See `doc/asmr_generation_flow.md`)
        2. リアルなASMRを実現するための技術調査を行う。(`doc/asmr_library_research.md` の内容を再確認・拡充する)
        3. `spatial_plan_agent` を改善し、脚本からより詳細で適切な音響空間プラン（音の定位、動き、環境音など）を生成できるようにする。
        4. `asmr_agent` (および内部で使われる `binaural_renderer` ツール) を改善し、空間プランに基づいたリバーブや音の移動をより自然に表現できるようにする。
    - **ゴール**: ユーザーが生成されたASMR音声を聞いた際に、まるでその場にいるかのようなリアルな没入感を得られるようにする。

### P1: 品質と安定性の向上

- [ ] **エラーハンドリングの強化**
    - **内容**: 各エージェントのAPI呼び出しやファイルI/Oでエラーが発生した場合の、リトライやフォールバック処理を実装する。
    - **対象**: 全てのエージェント (`script_agent`, `tts_agent`, `jsonize_agent`, `spatial_plan_agent`, `asmr_agent`)

- [ ] **JSONバリデーションの導入**
    - **内容**: `jsonize_agent` と `spatial_plan_agent` が生成するJSONの形式が正しいか検証する処理を追加する。不正な場合はエラーハンドリングを行う。
    - **対象**: `jsonize_agent`, `spatial_plan_agent`

- [ ] **出力管理の改善**
    - **内容**: 生成される全ての中間ファイルと最終成果物を、実行ごとにタイムスタンプ付きのユニークなディレクトリに保存するように変更する。
    - **対象**: `tts_agent`, `jsonize_agent`, `spatial_plan_agent`, `asmr_agent`

### P2: メンテナンス性と拡張性の向上

- [ ] **テストコードの導入**
    - **内容**: 各エージェントの単体テストと、`SequentialAgent` の全体的な動作を検証する結合テストを作成する。
    - **具体的な作業**:
        1. [x] 各エージェントとツールの単体テスト計画を作成する (`doc/testplan.md`)。
        2. [x] `testplan.md` に基づき、各エージェントの単体テストを実装する。 (`script`, `tts`, `jsonize`, `spatial_plan`)
        3. [x] `testplan.md` に結合テストの計画を追記する。
        4. [ ] エージェント間の連携を検証する結合テストを実装する。
    - **ゴール**: 将来の機能追加やリファクタリングを安全に行えるようにする。

## 完了済み

### P0: 最優先タスク（アプリケーションの正常化）

- [x] **`binaural_renderer`ツールの修正**
    - **内容**: `asmr_agent` と `BinauralRenderer` ツールの間のインターフェースの不整合を解消する。
    - **ファイル**: `asmr_gen_adk/tools/binaural_renderer.py`
    - **具体的な作業**:
        1. `make_asmr_audio` 関数から、現在使用していない `script_json` 引数を削除する。
        2. `BinauralRenderer` ツール関数から、`script_json` に関連する処理を削除する。
    - **ゴール**: `asmr_agent` が渡すデータ（モノラル音声と空間プラン）だけで、バイノーラル音声が正しく生成されるようにする。

### P2: メンテナンス性と拡張性の向上

- [x] **設定の外部化**
    - **内容**: コード内にハードコーディングされているモデル名 (`gemini-2.5-pro` 等) やTTSのボイス名 (`Kore` 等) を、設定ファイル（例: `config.yaml`）に分離する。
    - **対象**: `script_agent`, `tts_agent`, `jsonize_agent`, `spatial_plan_agent`, `asmr_agent`