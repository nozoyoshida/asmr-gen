# ASMR-GEN 改善計画（睡眠導入 / 恋人ささやきボイス特化）
**ファイル**: `asmr_improvement_plan.md`  
**対象バージョン**: 現行（ADK + `spatial_plan_agent` / `asmr_agent` / `BinauralRenderer` 構成） → 次期 v1.0  
**主目的**: ① 睡眠導入に最適化された“やさしい没入感”、② 擬似恋愛・恋人ささやき用途に特化した“近接・親密感”の両立。

---

## 0. 要約（What will change?）
- **プロファイル二軸最適化**：「Sleep」/「Whisper（恋人）」の**設計指針・数値レンジ**を定義（距離・方位・移動速度・リバーブ・EQ・ラウドネス）。  
- **空間プラン生成の堅牢化**：`spatial_plan_agent`に**物理的・聴覚的制約**（移動速度/距離/方位の微動）をプロンプトで強制、**自動スムージング**と**異常検知**で不自然さを削減。  
- **レンダラー強化**：`BinauralRenderer`で**クロスフェード窓の改良**、**HRTF補間**、**距離減衰+高域減衰**、**可変ブロック**、**後段マスタリング**（LUFS/リミッタ/デエッサ/ノイズフロア整形）。  
- **リバーブ適正化**：アルゴリズム/IRの**シーン別プリセット**、**プリディレイ/ローカット/ハイカット**、**発話ポーズ検出に応じたゲーティング**で“かけ過ぎ”を防止。  
- **QA/MUSHRA**：ABテスト手順・メトリクス（動きの自然さ/疲労度/眠気誘発度/親密度）を定義し、**数値管理**を導入。

---

## 1. 成功指標（KPI）
| 指標 | Sleep プロファイル | Whisper（恋人）プロファイル | 備考 |
|---|---:|---:|---|
| ラウドネス（Integrated LUFS） | -20 ～ -18 LUFS | -19 ～ -17 LUFS | 長尺聴取の疲労を回避しつつ知覚音量の安定化 |
| True Peak | ≤ -1.0 dBTP | ≤ -1.0 dBTP | クリップ/インターサンプルピーク対策 |
| Sibilance（5–8 kHz 帯域） | 相対 -18 dB 以下 | 相対 -15 dB 以下 | デエッサ適用基準 |
| 動きの滑らかさ（隣接キー間の角速度） | ≤ 40°/秒 | ≤ 60°/秒 | 早すぎるパンは疲労感 |
| 不自然ジャンプ検出件数 | 0/分 | 0/分 | 角度/距離の急変を自動拒否 |
| リバーブ過多フラグ（平均Mix） | ≤ 0.25 | ≤ 0.18 | 発話主体はドライ寄りが自然 |

---

## 2. プロファイル設計（Sleep / Whisper）
### 2.1 空間パラメータの推奨レンジ
| パラメータ | Sleep | Whisper（恋人） | 理由 |
|---|---|---|---|
| 距離 `distance` (m) | 0.18–0.35 | **0.08–0.15** | 恋人用途は**至近距離**で近接感を最大化。Sleepはやや離し疲労低減 |
| 方位 `azimuth` (°) | ±15～±120 の範囲で**ゆっくり周回** | **±85～±110**中心（耳後方に回り込みは最小限） | 近接囁きは耳介近傍が最も親密 |
| 仰角 `elevation` (°) | -10～+10 | -5～+5 | 近接での上下変化は最小限が自然 |
| 角速度（平均） | 10–25°/s | 15–35°/s | Whisperは**微小な揺れ**を多用 |
| マイクロジッタ | ±2–5°/0.5–1.5s | **±3–8°/0.3–1.0s** | 微細頭部運動の錯覚を付与 |
| リバーブMix | 0.08–0.25 | **0.04–0.18** | 近接囁きは基本**ドライ優先** |
| ルームサイズ（擬似） | 0.35–0.55 | **0.25–0.40** | 小部屋/ベッドサイド感 |
| プリディレイ | 5–20 ms | **3–12 ms** | 直音優先で距離感を保つ |

### 2.2 トーン・ダイナミクス
- **Sleep**: HPF 40–60 Hz（低域ブーミー回避）、緩やかな**Tilt EQ**（+1 dB/Oct で高域抑制）、**微量ブラウノイズ**（-50 ～ -45 dBFS）で包まれ感。  
- **Whisper**: **デエッサ（5–8 kHz）**軽度、**近接EQ**（200–500 Hz を +1～+2 dB で温かみ）、**空気感**（12–16 kHz +0.5～+1 dB）を状況に応じて。

---

## 3. TTS / 台本 / 収録前処理
1. **SSML（もしくは相当API）設計**  
   - `rate`: Sleep 0.85–0.92、Whisper 0.92–0.98  
   - `volume`: Sleep -6 ～ -4 dB、Whisper -4 ～ -2 dB  
   - `break`: 句点後 300–700 ms、寝息/間を**意図的に**挿入。  
   - 子音強調は控えめ、`<prosody pitch="-2st">`で柔らかく。  
2. **サイレンス整形**：文頭/文末に 150–400 ms の無音（ポーズ検出にも使用）。  
3. **プリプロ**：軽度デエッサ→ノーマライズ（-3 dBFS）→`BinauralRenderer` へ。

---

## 4. `spatial_plan_agent` 改善（生成側）
### 4.1 プロンプト規範（追加ルール）
- **物理/聴覚制約**を**明示**：  
  - 連続キーフレームの**角速度 ≤ 60°/s（Whisper）/ 40°/s（Sleep）**。  
  - **距離差 ≤ 0.05 m/秒**、**方位差 ≤ 25°/秒**。  
  - Whisper は**方位中心を±90〜110°**に“留める”フェーズを多用。  
- **マイクロジッタ生成**：±(3–8)°を 0.3–1.0 s 間隔（Whisper）/ ±(2–5)°を 0.5–1.5 s（Sleep）。  
- **リバーブMixの上限**：Whisper 0.18、Sleep 0.25。**静寂/囁きの直後は Mix を自動減衰**。  
- **キータイミング整合**：`timed_script_json` の発話開始/終端と**同期**。  
- **出力は JSON 配列のみ**（Markdownブロック禁止）。

### 4.2 自動スムージング/バリデーション（実装）
```python
# plan_smoother.py（新規）
def smooth_and_validate(plan, fs, max_deg_per_s=50, max_dr_per_s=0.05):
    plan = enforce_json_schema(plan)  # 欠損/型/範囲チェック
    plan = cubic_smooth(plan, keys=["azimuth","elevation","distance"], tension=0.4)
    plan = clamp_speed(plan, max_deg_per_s, max_dr_per_s)  # 速度上限
    plan = clamp_ranges(plan, az=(-170,170), el=(-30,30), dist=(0.07,0.6))
    plan = limit_reverb(plan, max_mix=0.25)
    detect_and_fix_jumps(plan, thresh_deg=30, thresh_dr=0.07)
    return plan
```
- `asmr_agent` の実行前に **必ず通す**。異常時は**自動修正 or リジェクト**。

---

## 5. `BinauralRenderer` 改善（再生側DSP）
### 5.1 コア
- **クロスフェード窓**：線形→**Raised Cosine（Hann）**へ。移行しながら**パラメータ変化時のみ**2経路合成。  
- **可変ブロック**：移動速度に応じて `block_size` を **768–2048**で自動。  
- **HRTF補間**：方位・仰角の**双線形補間**（欠測時は近傍3点で重み付け）。  
- **距離減衰**：`gain = 1 / max(0.1, distance)` に**高域減衰**（空気吸収）を併用：  
  - `HF_cut(distance) ≈ lowpass(fc = 16kHz / (1 + 4*distance))`  
- **近接補正**：`distance < 0.12 m`で**近接効果の過多低減**（200 Hz 付近 -1～-2 dB）。

### 5.2 リバーブ設計
- **アルゴ/IRハイブリッド**：デフォルトは `pedalboard.Reverb` を**控えめ**に。オプションで**小部屋IR**（クローゼット/ベッドルーム）を選択可。  
- **プリディレイ/ローカット/ハイカット**：`hp 120–180 Hz`, `lp 9–12 kHz`。  
- **発話ポーズ検出ゲート**：無音区間では `mix → mix*0.5`、復帰は 100–250 ms でスムーズ。

### 5.3 後段マスタリング（レンダラー内 or 後処理）
1. **K-weighted LUFS** を計測し **ターゲット正規化**（Sleep -19 LUFS、Whisper -18 LUFS）。  
2. **ソフトリミッタ**（Ceiling -1.0 dBTP, GR ≤ 3 dB）。  
3. **デエッサ**（5–8 kHz, 2–4 dB）。  
4. **Dither**（16-bit 出力時）。  
5. **ノイズフロア整形**：Sleep は -50 dBFS 付近で**微量ブラウノイズ**を敷くプリセット。

---

## 6. コンフィグ化（YAML 例）
```yaml
profiles:
  sleep:
    distance_range: [0.18, 0.35]
    azimuth_core: [-120, 120]
    elevation_range: [-10, 10]
    avg_ang_speed_dps: [10, 25]
    micro_jitter_deg: [2, 5]
    micro_jitter_period_s: [0.5, 1.5]
    reverb_mix_max: 0.25
    room_size: [0.35, 0.55]
    predelay_ms: [5, 20]
    target_lufs: -19
  whisper:
    distance_range: [0.08, 0.15]
    azimuth_core: [85, 110]
    elevation_range: [-5, 5]
    avg_ang_speed_dps: [15, 35]
    micro_jitter_deg: [3, 8]
    micro_jitter_period_s: [0.3, 1.0]
    reverb_mix_max: 0.18
    room_size: [0.25, 0.4]
    predelay_ms: [3, 12]
    target_lufs: -18

renderer:
  block_size_min: 768
  block_size_max: 2048
  crossfade_window: "hann"
  distance_attenuation: "1_over_r"
  air_absorption: true
  nearfield_comp_threshold_m: 0.12
  limiter_ceiling_db: -1.0
  deesser_band_hz: [5000, 8000]
  add_brown_noise_sleep_dbfs: -50
  output_bit_depth: 24
```

---

## 7. 具体的なバグ/課題への対処
- **リバーブ過剰**：  
  - `spatial_plan_agent` 側で `reverb_mix` の**上限**と**会話直後の減衰**を規定。  
  - レンダラーで**プリディレイ/HPF/LPF/ゲート**を標準化。  
- **定位・移動の不自然さ**：  
  - **角速度/距離速度のハード制約**と**スムージング**導入。  
  - **マイクロジッタ**をモデル化（規則でなく確率的に）。  
  - レンダラーで**Raised Cosineクロスフェード**と**可変ブロック**。

---

## 8. QA/評価設計
- **客観指標**：
  - 角速度超過/距離ジャンプ検出件数、平均リバーブMix、LUFS/TP、デエッサ稼働率。  
- **主観評価（MUSHRA 近似）**：
  - スコア軸：没入感、疲労度、眠気誘発度（Sleep）、親密度（Whisper）、定位の自然さ。  
  - 被験者 N=8–12、各 3 分×3 条件（現行/改善A/改善B）。  
- **合格基準**：既存比 +10pt（100点法）以上、疲労度は -10pt 以上改善。

---

## 9. 実装手順（優先度順）
1. `plan_smoother.py` の導入（スキーマ検証/速度制限/上限クリップ/スプライン）。  
2. `BinauralRenderer`：クロスフェード窓を Hann、可変ブロック、自動LP（距離に応じた高域減衰）。  
3. リバーブ列：プリディレイ/HPF/LPF/ゲートの追加と既定値。  
4. 後段：LUFS正規化 + リミッタ + デエッサ + ノイズ整形。  
5. `spatial_plan_agent` プロンプトの改訂と**ユニットテスト**（角速度/距離速度/上限チェック）。  
6. YAML プロファイル読込に対応し、`sleep` / `whisper` を**コマンドライン切替**。  
7. ABテスト → パラメータ確定 → v1.0 タグ。

---

## 10. 追加サンプル（Whisper用 SSMLイメージ）
> 実際の TTS 実装に合わせてタグ名・属性は調整してください。

```xml
<speak>
  <prosody rate="0.95" volume="-3dB" pitch="-2st">
    ねぇ、今日はもう無理しないで……。
    <break time="500ms"/>
    ゆっくり、目を閉じて。
    <break ti