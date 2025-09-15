# ASMR音声生成フロー解説 (詳細版)

このドキュメントは、ASMR-GENプロジェクトにおけるASMR音声生成の技術的な仕組み、特に `spatial_plan_agent` と `asmr_agent` の連携、および `binaural_renderer` ツール内部の処理について、実際のコードを交えて詳細に解説する。

## 1. 全体フロー

ASMR音声の生成は、以下のエージェントとツールが連携して実行される。

```mermaid
graph TD
    A[timed_script_json<br/>(タイムスタンプ付き脚本)] --> B(spatial_plan_agent);
    C[wav_path<br/>(モノラル音声)] --> B;
    B --> D{spatial_plan_json<br/>(空間プラン)};
    D --> E(asmr_agent);
    C --> E;
    E -- ツール呼び出し --> F[BinauralRenderer Tool];
    F --> G[binaural_output_path<br/>(バイノーラル音声)];
```

1.  **`spatial_plan_agent`**: `tts_agent`が生成したモノラル音声 (`wav_path`) と、タイムスタンプ付きの脚本 (`timed_script_json`) を入力として受け取る。脚本の内容と音声のタイミングを分析し、音の空間的な配置計画 (`spatial_plan_json`) をJSON形式で出力する。
2.  **`asmr_agent`**: `spatial_plan_agent`が生成した空間プランと、元のモノラル音声を入力として受け取る。これらを `BinauralRenderer` ツールに渡し、バイノーラル音声のレンダリングを指示する。
3.  **`BinauralRenderer` Tool**: `asmr_agent`から呼び出され、実際の音声処理を実行する。モノラル音声を空間プランに従って動的に定位させ、リバーブなどを適用して最終的なバイノーラル音声ファイルを生成する。

---

## 2. 各コンポーネントの詳細

### 2.1. `spatial_plan_agent`

-   **役割**: 脚本と音声のタイミング情報から、没入感のあるASMR体験を実現するための「音響空間プラン」を立案するサウンドデザイナー。
-   **入力**:
    -   `timed_script_json`: 各セリフの開始・終了時刻が記録されたJSON。
    -   `wav_path`: TTSが生成したモノラル音声ファイルのパス。
-   **処理**: LLM (Gemini) に対して、脚本の内容（「右耳元で囁く」などの指示）と音声のタイミングを考慮し、キーフレームベースの空間プランを作成するよう指示する。プロンプト内で厳密なJSON出力形式を指定している。
-   **出力 (`spatial_plan_json`)**: キーフレームオブジェクトのJSON配列。
    -   **キーフレームの構造**:
        ```json
        {
          "time": float,       // イベントが発生する時刻 (秒)
          "azimuth": float,    // 方位角 (-180° ~ 180°, 0°が正面, 90°が右)
          "elevation": float,  // 仰角 (-90° ~ 90°, 0°が水平)
          "distance": float,   // 距離 (メートル)
          "reverb_mix": float  // リバーブのミックス比率 (0.0 ~ 1.0)
        }
        ```

#### 該当コード (`asmr_gen_adk/agents/spatial_plan_agent.py`)

エージェントの定義と、LLMへの指示を生成するプロンプトは以下の通り。

```python
import json
import yaml
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the spatial plan agent."""
    script_json = await inject_session_state("{timed_script_json}", readonly_ctx)
    wav_path = await inject_session_state("{wav_path}", readonly_ctx)

    # The prompt is in a separate file, but we pass the wav_path for context.
    # The model will use its multi-modal capabilities to analyze the audio.
    # We are also passing the script content explicitly in the prompt.
    return (
        "You are a professional sound designer specializing in ASMR. "
        "Your task is to create a spatial audio plan (as a JSON array of keyframes) "
        "based on the provided script and the timing of the accompanying audio file. "
        "Analyze the script for movement cues and the audio for pacing and pauses. "
        "The keyframes should create a natural and immersive experience."
        "\n\n"
        "## Input Script (JSON):"
        f"```json\n{script_json}\n```"
        "\n"
        "## Input Audio File Path (for timing reference):"
        f"{wav_path}"
        "\n\n"
        "## Output Format Requirements:"
        "- A JSON array of keyframe objects."
        "- Each keyframe: {time: float, azimuth: float, elevation: float, distance: float, reverb_mix: float}"
        "- The `time` of each keyframe must align with the events in the audio file."
        "- Output ONLY the JSON array."
        "\n\n"
        "Now, create the spatial plan."
    )

spatial_plan_agent = LlmAgent(
    name="spatial_plan_agent",
    model=config["models"]["spatial_plan_agent"], # Assuming this model has multi-modal capabilities
    description="Creates a spatial audio plan from a script and audio file.",
    instruction=_build_instruction,
    output_key="spatial_plan_json",
)
```

---

### 2.2. `asmr_agent`

-   **役割**: 空間プランとモノラル音声を受け取り、`BinauralRenderer` ツールを正しく呼び出す最終的なオーディオエンジニア。
-   **入力**:
    -   `spatial_plan_json`: `spatial_plan_agent` が生成した空間プラン。
    -   `wav_path`: TTSが生成したモノラル音声ファイルのパス。
-   **処理**: 受け取った入力から、`BinauralRenderer` ツールを呼び出すためのPythonコード文字列をプロンプト内で組み立てる。LLMはこのプロンプトに従い、ツール呼び出しを実行する。
-   **出力**: `binaural_output_path`: 生成されたバイノーラル音声ファイルのパス。

#### 該当コード (`asmr_gen_adk/agents/asmr_agent.py`)

`spatial_plan_agent` が生成したJSONからMarkdownフォーマットを除去し、ツール呼び出し用のプロンプトを生成する。

```python
import os
import re
import yaml
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state
from ..tools.binaural_renderer import BinauralRenderer

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

ASMR_AGENT_MODEL = config["models"]["asmr_agent"]

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the ASMR agent."""
    wav_path = await inject_session_state("{wav_path}", readonly_ctx)
    spatial_plan_json = await inject_session_state("{spatial_plan_json}", readonly_ctx)

    # Clean up the spatial plan JSON by removing markdown formatting
    # Use regex to find the JSON block, allowing for surrounding text/whitespace
    match = re.search(r'```(json)?\s*([\s\S]*?)\s*```', spatial_plan_json)
    if match:
        spatial_plan_json = match.group(2).strip()


    # Define the output path for the final binaural audio
    output_dir = "asmr_gen_adk/output/binaural_audio"
    base_name = os.path.basename(wav_path)
    binaural_output_path = os.path.join(output_dir, f"binaural_{base_name}")

    return f"""You are the final audio processing engineer. Your task is to render the binaural ASMR audio using the provided mono audio file and the spatial plan.

1. **Mono Audio Path:** `{wav_path}`
2. **Spatial Plan JSON:** `{spatial_plan_json}`
3. **Output Path:** `{binaural_output_path}`

Use the `BinauralRenderer` tool to perform the rendering. Call the tool with: `BinauralRenderer(mono_audio_path='{wav_path}', spatial_plan_json='''{spatial_plan_json}''', output_path='{binaural_output_path}')`

Upon completion, output only the path to the final binaural audio file.
"""

asmr_agent = LlmAgent(
    name="asmr_agent",
    model=ASMR_AGENT_MODEL,
    description="Renders a mono audio file into a binaural ASMR WAV file.",
    instruction=_build_instruction,
    tools=[BinauralRenderer],
    output_key="binaural_output_path",
)
```

---

### 2.3. `BinauralRenderer` ツール

-   **役割**: 実際のバイノーラル音声レンダリング処理を担うPython関数。
-   **コア技術**:
    -   **HRTF (頭部伝達関数)**: `spaudiopy` ライブラリを使用し、HRTFをロードする。
    -   **動的レンダリング**: `scipy.interpolate.interp1d` でキーフレーム間を線形補間し、滑らかな音の移動を実現する。
    -   **Input Crossfading**: 音源位置が変化する際のクリックノイズを防ぐため、音声ブロックごとにパラメータを更新し、古いパラメータと新しいパラメータで処理した音声をクロスフェードする。
    -   **動的リバーブ**: `pedalboard` ライブラリを使用し、ステレオリバーブを生成・ミックスする。

#### 該当コード (`asmr_gen_adk/tools/binaural_renderer.py`)

##### ツールラッパー関数

ADKから直接呼び出されるインターフェース。ファイルI/OとJSONのパースを行い、メインのレンダリング関数 `make_asmr_audio` を呼び出す。

```python
def BinauralRenderer(mono_audio_path: str, spatial_plan_json: str, output_path: str) -> Dict[str, str]:
    """
    Tool wrapper for make_asmr_audio function.
    Reads input files, calls the renderer, and saves the output.
    """
    try:
        # 1. Read audio data
        audio_data, sample_rate = sf.read(mono_audio_path)

        # 2. Load JSON data
        spatial_plan = json.loads(spatial_plan_json)

        # 3. Call the rendering function
        output_audio, output_sr = make_asmr_audio(
            audio_data=audio_data,
            sample_rate=sample_rate,
            spatial_plan_json=spatial_plan
        )

        # 4. Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # 5. Save the output file
        sf.write(output_path, output_audio, output_sr)

        # 6. Verify that the file was written
        if not os.path.exists(output_path):
            raise IOError(f"Failed to write output file to {output_path}")

        return {"binaural_output_path": output_path}
    except Exception as e:
        logging.error(f"Binaural rendering failed in tool wrapper: {e}", exc_info=True)
        return {"error": f"Binaural rendering failed: {str(e)}"}
```

##### メインレンダリング関数

音声処理全体のフローを管理する。

```python
def make_asmr_audio(audio_data: np.ndarray, sample_rate: int, spatial_plan_json: List[Dict[str, Any]]) -> Tuple[np.ndarray, int]:
    """
    モノラル音声と空間プランからバイノーラル音声をレンダリングする。
    """
    logging.info("Starting ASMR rendering...")

    # 1. 前処理とリサンプリング
    audio_float = _preprocess_audio(audio_data, sample_rate)
    duration_sec = len(audio_float) / TARGET_FS

    # 2. HRTFのロード
    hrtf = _load_hrtf(TARGET_FS)

    # 3. 空間プランの補間関数の作成
    interpolators = _create_interpolators(spatial_plan_json, duration_sec)

    # 4. 動的バイノーラルレンダリング (Dry信号生成)
    output_dry = _render_binaural_dynamic_crossfade(audio_float, hrtf, interpolators)

    # 5. リバーブ処理とミックス
    output_final = _apply_dynamic_reverb(output_dry, interpolators)

    # 6. 後処理（正規化とトリミング）
    output_final = _postprocess_audio(output_final, len(audio_float))

    logging.info("Rendering finished.")
    return output_final, TARGET_FS
```

##### 動的バイノーラルレンダリング (Input Crossfading)

音の移動を滑らかに実現する核心部分。

```python
def _render_binaural_dynamic_crossfade(audio_data, hrtf, interpolators, block_size=1024):
    """
    Input Crossfadingを用いて動的にバイノーラルレンダリングを行う。
    音源移動時のノイズを効果的に抑制する。
    """
    logging.info("Rendering binaural audio (Dry signal) using Input Crossfading...")
    N = len(audio_data)
    hrir_len = hrtf.left.shape[1]
    output_dry = np.zeros((N + hrir_len, 2))

    # クロスフェード用のウィンドウ (線形、合計が1)
    fade_in = np.linspace(0, 1, block_size)
    fade_out = 1.0 - fade_in

    # 初期状態の設定
    start_time = 0.0
    azi = float(interpolators['azimuth'](start_time))
    ele = float(interpolators['elevation'](start_time))
    dist = float(interpolators['distance'](start_time))
    current_hrir, current_attenuation = _get_hrir_and_attenuation(hrtf, azi, ele, dist)
    last_params = (azi, ele, dist)

    # ブロック処理
    for start_idx in range(0, N, block_size):
        end_idx = min(start_idx + block_size, N)
        block = audio_data[start_idx:end_idx]
        actual_block_size = len(block)
        current_time = end_idx / TARGET_FS

        # 位置情報を補間
        azi = float(interpolators['azimuth'](current_time))
        ele = float(interpolators['elevation'](current_time))
        dist = float(interpolators['distance'](current_time))
        new_params = (azi, ele, dist)

        current_fade_out = fade_out[:actual_block_size]
        current_fade_in = fade_in[:actual_block_size]

        if new_params != last_params:
            # パラメータが変化した場合: Input Crossfading
            new_hrir, new_attenuation = _get_hrir_and_attenuation(hrtf, azi, ele, dist)
            block_fade_out = block[:, None] * current_fade_out[:, None]
            block_fade_in = block[:, None] * current_fade_in[:, None]
            binaural_old = scipy.signal.fftconvolve(block_fade_out, current_hrir, mode='full', axes=0) * current_attenuation
            binaural_new = scipy.signal.fftconvolve(block_fade_in, new_hrir, mode='full', axes=0) * new_attenuation
            binaural_block = binaural_old + binaural_new
            current_hrir, current_attenuation, last_params = new_hrir, new_attenuation, new_params
        else:
            # パラメータが変化しない場合: 通常の畳み込み
            binaural_block = scipy.signal.fftconvolve(block[:, None], current_hrir, mode='full', axes=0) * current_attenuation

        out_end_idx = start_idx + len(binaural_block)
        output_dry[start_idx:out_end_idx] += binaural_block

    return output_dry
```

##### 動的リバーブ適用

レンダリングされたドライ音源に、時間変化するリバーブを適用する。

```python
def _apply_dynamic_reverb(output_dry, interpolators):
    """リバーブを適用し、時間変化するミックス比率で合成する"""
    logging.info("Applying reverb and dynamic mixing...")
    
    # 1. Wet信号の生成 (リバーブ100%)
    board = Pedalboard([
        Reverb(room_size=0.6, damping=0.5, width=1.0, wet_level=1.0, dry_level=0.0)
    ])
    output_wet = board.process(output_dry.T.astype(np.float32), sample_rate=TARGET_FS).T

    # 2. 動的ミックス
    num_samples = output_dry.shape[0]
    time_axis = np.arange(num_samples) / TARGET_FS
    reverb_mix_values = interpolators['reverb_mix'](time_axis).reshape(-1, 1)
    reverb_mix_values = np.clip(reverb_mix_values, 0.0, 1.0)

    min_len = min(output_dry.shape[0], output_wet.shape[0])
    
    # 合成: Dry * (1 - Mix) + Wet * Mix
    output_final = (output_dry[:min_len] * (1.0 - reverb_mix_values[:min_len]) + 
                    output_wet[:min_len] * reverb_mix_values[:min_len])

    return output_final
```

---

## 3. 課題と改善の方向性

このドキュメントで明らかになった現状の実装に基づき、`doc/todo.md` に記載されている以下の課題に取り組む。

-   **リバーブが過剰**: `pedalboard.Reverb` のパラメータ (`room_size=0.6`, `damping=0.5` など) や、`spatial_plan_agent` が生成する `reverb_mix` の値が、シチュエーションに対して適切でない可能性がある。
-   **音の定位・移動が不自然**: `spatial_plan_agent` が生成する `azimuth`, `elevation`, `distance` の値が、脚本の意図を正確に反映できていない可能性がある。プロンプトの改善や、より高度な空間プランニングロジックの導入が考えられる。