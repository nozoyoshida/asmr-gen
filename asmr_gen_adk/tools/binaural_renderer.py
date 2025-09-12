import numpy as np
import json
import spaudiopy as spa
import scipy.signal
import scipy.interpolate
from pedalboard import Pedalboard, Reverb
import librosa
import soundfile as sf
from typing import Dict, List, Any, Tuple
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)

# 処理ターゲットのサンプリングレート。HRTFの品質を保つため48kHzとする。
TARGET_FS = 48000
MIN_DISTANCE = 0.2 # 距離減衰の最小値 (近接効果の制限)

def make_asmr_audio(audio_data: np.ndarray, sample_rate: int, spatial_plan_json: List[Dict[str, Any]]) -> Tuple[np.ndarray, int]:
    """
    モノラル音声と空間プランからバイノーラル音声をレンダリングする。

    Args:
        audio_data: 入力音声データ (モノラル推奨)
        sample_rate: 入力音声のサンプリングレート (例: 24000)
        spatial_plan_json: 空間プラン情報JSON

    Returns:
        Tuple[np.ndarray, int]: レンダリングされたバイノーラル音声データ (ステレオ)とサンプリングレート(TARGET_FS)
    """
    logging.info("Starting ASMR rendering...")

    # 1. 前処理とリサンプリング
    audio_float = _preprocess_audio(audio_data, sample_rate)
    duration_sec = len(audio_float) / TARGET_FS

    # 2. HRTFのロード
    # 標準的なHRTF (Neumann KU100) をロード。初回はダウンロードが発生する場合があります。
    hrtf = _load_hrtf(TARGET_FS)

    # 3. 空間プランの補間関数の作成
    interpolators = _create_interpolators(spatial_plan_json, duration_sec)

    # 4. 動的バイノーラルレンダリング (Dry信号生成)
    # Input Crossfadingを用いて滑らかな移動を実現
    output_dry = _render_binaural_dynamic_crossfade(audio_float, hrtf, interpolators)

    # 5. リバーブ処理とミックス
    output_final = _apply_dynamic_reverb(output_dry, interpolators)

    # 6. 後処理（正規化とトリミング）
    output_final = _postprocess_audio(output_final, len(audio_float))

    logging.info("Rendering finished.")
    return output_final, TARGET_FS

# --- ヘルパー関数群 ---

def _preprocess_audio(audio_data, sample_rate):
    """音声の前処理（モノラル化、float変換、リサンプリング）"""
    if audio_data.ndim > 1:
        logging.warning("Input audio is not monaural. Converting to mono.")
        audio_data = np.mean(audio_data, axis=1)

    # float型への変換
    if not np.issubdtype(audio_data.dtype, np.floating):
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        else:
            raise TypeError(f"Unsupported audio dtype: {audio_data.dtype}. Use float or int16.")

    # リサンプリング
    if sample_rate != TARGET_FS:
        logging.info(f"Resampling audio from {sample_rate} Hz to {TARGET_FS} Hz...")
        # 高品質なリサンプリング
        audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=TARGET_FS, res_type='soxr_hq')
    
    return audio_data.astype(np.float32)

def _load_hrtf(fs):
    """HRTFのロード"""
    logging.info("Loading HRTF...")
    try:
        return spa.io.load_hrirs(fs=fs)
    except Exception as e:
        logging.error(f"Failed to load HRTF: {e}")
        raise

def _create_interpolators(spatial_plan, duration):
    """空間プランから線形補間関数を作成する"""
    if not spatial_plan:
        # プランが空の場合のデフォルト設定
        default_plan = [{"time": 0.0, "azimuth": 0, "elevation": 0, "distance": 1.0, "reverb_mix": 0.1}]
        spatial_plan = default_plan

    times = np.array([p['time'] for p in spatial_plan])
    
    # プランが音声の開始・終了をカバーするように調整
    adjusted_times = times.copy()
    values_dict = {}

    for param in ['azimuth', 'elevation', 'distance', 'reverb_mix']:
        values = np.array([p[param] for p in spatial_plan])
        
        if times[0] > 0:
            values = np.insert(values, 0, values[0])
        if times[-1] < duration:
            values = np.append(values, values[-1])
        
        values_dict[param] = values

    if times[0] > 0:
        adjusted_times = np.insert(adjusted_times, 0, 0.0)
    if times[-1] < duration:
        adjusted_times = np.append(adjusted_times, duration)

    interpolators = {}
    for param, values in values_dict.items():
        # 線形補間関数を作成
        interpolators[param] = scipy.interpolate.interp1d(
            adjusted_times, values, kind='linear', bounds_error=False, fill_value=(values[0], values[-1])
        )
    return interpolators

def _get_hrir_and_attenuation(hrtf, azimuth, elevation, distance):
    """指定された位置のHRIRと距離減衰を取得する（座標変換を含む）"""
    # 座標変換: 
    # 入力JSON(右が正/時計回りと仮定) -> spaudiopy(左が正/反時計回り, 天頂角Zenithを使用)
    az_rad = np.deg2rad(-azimuth) 
    zen_rad = np.deg2rad(90 - elevation)
    
    # HRIRの取得 (最も近いHRIRを取得)
    hrir_l, hrir_r = hrtf.get_closest_hrir(az_rad, zen_rad)
    hrir = np.vstack([hrir_l, hrir_r]).T

    # 距離減衰 (1/dモデル)
    attenuation = 1.0 / max(distance, MIN_DISTANCE)
    
    return hrir, attenuation

def _render_binaural_dynamic_crossfade(audio_data, hrtf, interpolators, block_size=1024):
    """
    Input Crossfadingを用いて動的にバイノーラルレンダリングを行う。
    音源移動時のノイズを効果的に抑制する。
    """
    logging.info("Rendering binaural audio (Dry signal) using Input Crossfading...")
    N = len(audio_data)
    hrir_len = hrtf.left.shape[1]

    # 出力バッファの初期化
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

    # ブロック処理（非オーバーラップ）
    for start_idx in range(0, N, block_size):
        end_idx = min(start_idx + block_size, N)
        block = audio_data[start_idx:end_idx]
        actual_block_size = len(block)

        # ブロック終了時刻での位置情報を計算
        current_time = end_idx / TARGET_FS

        # 位置情報を補間
        azi = float(interpolators['azimuth'](current_time))
        ele = float(interpolators['elevation'](current_time))
        dist = float(interpolators['distance'](current_time))
        
        new_params = (azi, ele, dist)

        # 現在のブロック長に合わせてフェードウィンドウを調整
        current_fade_out = fade_out[:actual_block_size]
        current_fade_in = fade_in[:actual_block_size]

        if new_params != last_params:
            # パラメータが変化した場合: Input Crossfading
            
            # 1. 新しいパラメータの計算
            new_hrir, new_attenuation = _get_hrir_and_attenuation(hrtf, azi, ele, dist)

            # 2. 入力信号にクロスフェードウィンドウを適用
            # block[:, None]で(B, 1)に形状変更し、ウィンドウをブロードキャスト
            block_fade_out = block[:, None] * current_fade_out[:, None]
            block_fade_in = block[:, None] * current_fade_in[:, None]

            # 3. それぞれのHRIRで畳み込み (axes=0で時間軸方向に畳み込む)
            # 古いパラメータでの処理
            binaural_old = scipy.signal.fftconvolve(block_fade_out, current_hrir, mode='full', axes=0)
            binaural_old *= current_attenuation

            # 新しいパラメータでの処理
            binaural_new = scipy.signal.fftconvolve(block_fade_in, new_hrir, mode='full', axes=0)
            binaural_new *= new_attenuation

            # 4. 合成
            binaural_block = binaural_old + binaural_new

            # 5. パラメータ更新
            current_hrir = new_hrir
            current_attenuation = new_attenuation
            last_params = new_params

        else:
            # パラメータが変化しない場合: 通常の畳み込み
            binaural_block = scipy.signal.fftconvolve(block[:, None], current_hrir, mode='full', axes=0)
            binaural_block *= current_attenuation

        # 出力バッファへの加算 (畳み込みのテール部分が次のブロックに重なる)
        out_end_idx = start_idx + len(binaural_block)
        output_dry[start_idx:out_end_idx] += binaural_block

    return output_dry

def _apply_dynamic_reverb(output_dry, interpolators):
    """リバーブを適用し、時間変化するミックス比率で合成する"""
    logging.info("Applying reverb and dynamic mixing...")
    
    # 1. Wet信号の生成 (リバーブ100%)
    # バイノーラル化された信号に対してステレオリバーブを適用
    board = Pedalboard([
        # ASMRに適したリバーブ設定
        Reverb(room_size=0.6, damping=0.5, width=1.0, wet_level=1.0, dry_level=0.0)
    ], sample_rate=TARGET_FS)

    # 信号全体を通してリバーブ処理を行う
    # Pedalboardは(channels, samples)の形状を期待するため転置して処理し、元に戻す
    output_wet = board.process(output_dry.T.astype(np.float32)).T

    # 2. 動的ミックス
    num_samples = output_dry.shape[0]
    # サンプルごとの時間軸を生成
    time_axis = np.arange(num_samples) / TARGET_FS

    # ミックス比率の補間（全サンプルに対して行う）
    reverb_mix_values = interpolators['reverb_mix'](time_axis).reshape(-1, 1)
    reverb_mix_values = np.clip(reverb_mix_values, 0.0, 1.0)

    # Wet信号とDry信号の長さを揃える
    min_len = min(output_dry.shape[0], output_wet.shape[0])
    
    # 合成: Dry * (1 - Mix) + Wet * Mix
    output_final = (output_dry[:min_len] * (1.0 - reverb_mix_values[:min_len]) + 
                    output_wet[:min_len] * reverb_mix_values[:min_len])

    return output_final

def _postprocess_audio(output_audio, original_length):
    """後処理（正規化とトリミング）"""
    # 音声の長さを調整（コンボリューションやリバーブで伸びた末尾をカット）
    output_audio = output_audio[:int(original_length)]

    max_val = np.max(np.abs(output_audio))
    if max_val > 1.0:
        logging.warning(f"Output signal is clipping (max value: {max_val:.2f}). Normalizing.")
        output_audio /= max_val
    return output_audio

if __name__ == '__main__':
    # 1. 入力JSONの準備
    script_data = {
      "scene_elements": [
        # ... (省略) ...
      ]
    }

    spatial_plan_data = json.loads("""
    [
      {"time": 0.0, "azimuth": 10, "elevation": 0, "distance": 1.2, "reverb_mix": 0.3},
      {"time": 3.83, "azimuth": 5, "elevation": 0, "distance": 1.1, "reverb_mix": 0.3},
      {"time": 5.92, "azimuth": 0, "elevation": 0, "distance": 0.8, "reverb_mix": 0.2},
      {"time": 7.82, "azimuth": 0, "elevation": -5, "distance": 0.9, "reverb_mix": 0.2},
      {"time": 9.94, "azimuth": 5, "elevation": 0, "distance": 1.0, "reverb_mix": 0.3},
      {"time": 13.06, "azimuth": 45, "elevation": -5, "distance": 1.5, "reverb_mix": 0.4},
      {"time": 15.28, "azimuth": 55, "elevation": -5, "distance": 1.6, "reverb_mix": 0.4},
      {"time": 16.29, "azimuth": 20, "elevation": 0, "distance": 1.4, "reverb_mix": 0.3},
      {"time": 18.88, "azimuth": 60, "elevation": 5, "distance": 1.8, "reverb_mix": 0.5},
      {"time": 21.0, "azimuth": 60, "elevation": 10, "distance": 1.8, "reverb_mix": 0.5},
      {"time": 21.6, "azimuth": 40, "elevation": -20, "distance": 1.2, "reverb_mix": 0.3},
      {"time": 22.18, "azimuth": 15, "elevation": -15, "distance": 0.7, "reverb_mix": 0.1},
      {"time": 23.53, "azimuth": 10, "elevation": -10, "distance": 0.8, "reverb_mix": 0.1},
      {"time": 25.64, "azimuth": 10, "elevation": -10, "distance": 0.8, "reverb_mix": 0.1}
    ]
    """)

    # 2. 入力音声の準備 (ダミー音声の生成)
    INPUT_SR = 24000
    duration = 26.0 # 約26秒
    
    # ダミーとしてピンクノイズを生成
    logging.info("Generating dummy input audio (Pink Noise)...")
    num_samples = int(duration * INPUT_SR)
    # 簡易的なピンクノイズ生成
    white = np.random.uniform(-0.5, 0.5, num_samples)
    B, A = scipy.signal.butter(1, 1000/(INPUT_SR/2), btype='low')
    input_audio = scipy.signal.lfilter(B, A, white).astype(np.float32)

    # 3. 関数の実行
    try:
        output_audio, output_sr = make_asmr_audio(input_audio, INPUT_SR, spatial_plan_data)

        # 4. 結果の保存
        output_filename = "output_asmr_binaural_48k.wav"
        sf.write(output_filename, output_audio, output_sr)
        logging.info(f"""
Successfully saved binaural audio to {output_filename}""")
        logging.info(f"Output Sample Rate: {output_sr} Hz. Please listen with headphones.")
    except Exception as e:
        logging.error(f"""
An error occurred during processing: {e}""", exc_info=True)


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
        
        # The new make_asmr_audio function requires a script_json, which is not provided by the agent.
        # We'll pass an empty dict.
        script_data = {}

        # 3. Call the rendering function
        output_audio, output_sr = make_asmr_audio(
            audio_data=audio_data,
            sample_rate=sample_rate,
            spatial_plan_json=spatial_plan
        )

        # 4. Save the output file
        sf.write(output_path, output_audio, output_sr)

        return {"binaural_output_path": output_path}
    except Exception as e:
        logging.error(f"Binaural rendering failed in tool wrapper: {e}", exc_info=True)
        return {"error": f"Binaural rendering failed: {str(e)}"}
