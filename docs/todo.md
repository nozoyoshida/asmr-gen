# ASMR-GEN 開発ToDoリスト

## これから着手

### P0: ASMR品質の向上 (改善計画に基づく)

- [ ] **Phase 1: 基礎品質の向上**
    - [ ] **リバーブ処理の最適化**: `BinauralRenderer` のデフォルトパラメータをASMRに適したものに見直す (`room_size=0.2`, `damping=0.8` 等)。 ([plan §3.1](asmr_improvement_plan.md))
    - [ ] **`spatial_plan_agent` プロンプト強化**: 物理的制約（最大移動速度など）と距離・リバーブの連動を指示し、不自然なプラン生成を抑制する。 ([plan §2.1](asmr_improvement_plan.md))
    - [ ] **音像移動の平滑化**: キーフレーム間の補間を線形から3次スプライン補間に変更し、滑らかな動きを実現する。 ([plan §3.4](asmr_improvement_plan.md))

- [ ] **Phase 2: リアリティと快適性の追求**
    - [ ] **近接効果の導入**: `BinauralRenderer` に距離連動のEQを追加し、耳元での囁きのリアルさを向上させる。（最重要） ([plan §3.2](asmr_improvement_plan.md))
    - [ ] **ディエッサーの導入**: ポストプロダクション処理としてディエッサーを追加し、歯擦音を低減する。 ([plan §4.1](asmr_improvement_plan.md))
    - [ ] **マスタリング処理の導入**: ラウドネスノーマライゼーションと最終EQ調整を行い、聴感品質を安定させる。 ([plan §4.2](asmr_improvement_plan.md))
    - [ ] **マルチモーダル分析の活用**: `spatial_plan_agent` のプロンプトを改善し、音声の抑揚に基づいた距離感の演出を指示する。 ([plan §2.2](asmr_improvement_plan.md))

- [ ] **Phase 3: 高度な空間表現**
    - [ ] **空気吸収のシミュレーション**: `BinauralRenderer` に距離連動のLPF/ハイシェルフフィルタを追加し、距離感をよりリアルにする。 ([plan §3.3](asmr_improvement_plan.md))
    - [ ] **畳み込みリバーブの導入検討**: アルゴリズミックリバーブから畳み込みリバーブへの移行を調査・実装する。 ([plan §3.1](asmr_improvement_plan.md))
    - [ ] **空間プランパラメータの拡張**: `spatial_plan_json` にリバーブの質を動的に変更するパラメータを追加する。 ([plan §2.3](asmr_improvement_plan.md))

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

- [x] **`binaural_renderer`ツールの修正** (P0)
- [x] **設定の外部化** (P2)
- [x] **現状のASMR音声生成フローのドキュメント化** (P0)
