import os
import numpy as np
import json
import spaudiopy as spa
import scipy.signal
import scipy.interpolate
from pedalboard import Pedalboard, Reverb, LowShelfFilter
import librosa
import soundfile as sf
from typing import Dict, List, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)

TARGET_FS = 48000
MIN_DISTANCE = 0.1
PROXIMITY_THRESHOLD = 0.5

def make_asmr_audio(audio_data: np.ndarray, sample_rate: int, spatial_plan_json: List[Dict[str, Any]]) -> Tuple[np.ndarray, int]:
    logging.info("Starting ASMR rendering (Crystal Clear Mode)...")

    # 1. 前処理
    audio_float = _preprocess_audio(audio_data, sample_rate)
    duration_sec = len(audio_float) / TARGET_FS

    # 2. HRTFのロード
    hrtf = _load_hrtf(TARGET_FS)

    # 3. 空間プランの補間関数作成
    interpolators = _create_interpolators(spatial_plan_json, duration_sec)

    # 4. 動的バイノーラルレンダリング (Dry信号)
    output_dry, distance_curve = _render_binaural_dynamic_crossfade(audio_float, hrtf, interpolators)

    # 5. 近接効果（低音ブースト）のみ微適用
    avg_distance = np.mean(distance_curve)
    output_processed = _apply_proximity(output_dry, avg_distance)

    # 6. リバーブ処理（極小）
    output_final = _apply_dynamic_reverb(output_processed, interpolators)

    # 7. 後処理
    max_val = np.max(np.abs(output_final))
    if max_val > 0:
        # ピークギリギリまで音量を戻してクリアさを保つ
        target_peak = 0.98
        output_final = output_final * (target_peak / max_val)

    output_final = _postprocess_audio(output_final, len(audio_float))

    logging.info("Rendering finished.")
    return output_final, TARGET_FS

# --- ヘルパー関数群 ---

def _preprocess_audio(audio_data, sample_rate):
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)
    if not np.issubdtype(audio_data.dtype, np.floating):
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        else:
            audio_data = audio_data.astype(np.float32)
    audio_data = np.squeeze(audio_data)
    if sample_rate != TARGET_FS:
        # リサンプリングの劣化を防ぐため最高品質を指定
        audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=TARGET_FS, res_type='soxr_vhq')
    return audio_data.astype(np.float32)

def _load_hrtf(fs):
    try:
        return spa.io.load_hrirs(fs=fs)
    except Exception:
        return spa.io.load_hrirs(fs=fs)

def _create_interpolators(spatial_plan, duration):
    if not spatial_plan:
        default_plan = [{"time": 0.0, "azimuth": 0, "elevation": 0, "distance": 1.0, "reverb_mix": 0.0}]
        spatial_plan = default_plan
    times = np.array([p['time'] for p in spatial_plan])
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
        interpolators[param] = scipy.interpolate.interp1d(
            adjusted_times, values, kind='linear', bounds_error=False, fill_value=(values[0], values[-1])
        )
    return interpolators

def _get_hrir_and_attenuation(hrtf, azimuth, elevation, distance):
    az_rad = np.deg2rad(-azimuth) 
    zen_rad = np.deg2rad(90 - elevation)
    x_hrtf, y_hrtf, z_hrtf = spa.utils.sph2cart(hrtf.azi, hrtf.zen)
    x_target, y_target, z_target = spa.utils.sph2cart(az_rad, zen_rad)
    distances = np.sqrt((x_hrtf - x_target)**2 + (y_hrtf - y_target)**2 + (z_hrtf - z_target)**2)
    nearest_idx = np.argmin(distances)
    hrir_l = hrtf.left[nearest_idx, :]
    hrir_r = hrtf.right[nearest_idx, :]
    hrir = np.vstack([hrir_l, hrir_r]).T
    eff_distance = max(distance, MIN_DISTANCE)
    attenuation = 1.0 / (eff_distance ** 1.0) 
    return hrir, attenuation

def _render_binaural_dynamic_crossfade(audio_data, hrtf, interpolators, block_size=1024):
    N = len(audio_data)
    hrir_len = hrtf.left.shape[1]
    output_dry = np.zeros((N + hrir_len, 2))
    distance_curve = np.zeros(N)
    fade_in = np.linspace(0, 1, block_size)
    fade_out = 1.0 - fade_in
    start_time = 0.0
    azi = float(interpolators['azimuth'](start_time))
    ele = float(interpolators['elevation'](start_time))
    dist = float(interpolators['distance'](start_time))
    jitter_azi = np.random.normal(0, 1.0)
    current_hrir, current_attenuation = _get_hrir_and_attenuation(hrtf, azi + jitter_azi, ele, dist)
    last_params = (azi, ele, dist)
    for start_idx in range(0, N, block_size):
        end_idx = min(start_idx + block_size, N)
        block = audio_data[start_idx:end_idx]
        actual_block_size = len(block)
        current_time = end_idx / TARGET_FS
        azi = float(interpolators['azimuth'](current_time))
        ele = float(interpolators['elevation'](current_time))
        dist = float(interpolators['distance'](current_time))
        distance_curve[start_idx:end_idx] = dist
        jitter_azi = np.random.normal(0, 0.5)
        new_params = (azi, ele, dist)
        current_fade_out = fade_out[:actual_block_size]
        current_fade_in = fade_in[:actual_block_size]
        if new_params != last_params:
            new_hrir, new_attenuation = _get_hrir_and_attenuation(hrtf, azi + jitter_azi, ele, dist)
            block_fade_out = block[:, None] * current_fade_out[:, None]
            block_fade_in = block[:, None] * current_fade_in[:, None]
            binaural_old = scipy.signal.fftconvolve(block_fade_out, current_hrir, mode='full', axes=0) * current_attenuation
            binaural_new = scipy.signal.fftconvolve(block_fade_in, new_hrir, mode='full', axes=0) * new_attenuation
            binaural_block = binaural_old + binaural_new
            current_hrir = new_hrir
            current_attenuation = new_attenuation
            last_params = new_params
        else:
            binaural_block = scipy.signal.fftconvolve(block[:, None], current_hrir, mode='full', axes=0) * current_attenuation
        out_end_idx = start_idx + len(binaural_block)
        output_dry[start_idx:out_end_idx] += binaural_block
    return output_dry, distance_curve

def _apply_proximity(output_dry, avg_distance):
    """近接効果（透明度優先）"""
    logging.info(f"Applying proximity effect (avg distance: {avg_distance:.2f}m)")
    # 歪み系エフェクトは全て削除し、純粋なEQのみ
    if avg_distance < PROXIMITY_THRESHOLD:
        board = Pedalboard()
        # ブースト量を控えめに、Qを狭くして範囲を限定
        boost_db = min(2.0, (PROXIMITY_THRESHOLD - avg_distance) * 5)
        board.append(LowShelfFilter(cutoff_frequency_hz=150, gain_db=boost_db, q=1.0))
        processed = board.process(output_dry.T.astype(np.float32), sample_rate=TARGET_FS).T
        return processed
    else:
        # 近接していなければ何もしない
        return output_dry

def _apply_dynamic_reverb(output_dry, interpolators):
    logging.info("Applying tiny room reverb...")
    board = Pedalboard([
        Reverb(room_size=0.15, damping=0.6, wet_level=0.05, dry_level=1.0)
    ])
    output_wet = board.process(output_dry.T.astype(np.float32), sample_rate=TARGET_FS).T
    num_samples = output_dry.shape[0]
    time_axis = np.arange(num_samples) / TARGET_FS
    reverb_mix_values = interpolators['reverb_mix'](time_axis).reshape(-1, 1)
    reverb_mix_values = np.clip(reverb_mix_values, 0.0, 0.05) # 最大でも5%
    min_len = min(output_dry.shape[0], output_wet.shape[0])
    output_final = (output_dry[:min_len] * (1.0 - reverb_mix_values[:min_len]) + 
                    output_wet[:min_len] * reverb_mix_values[:min_len])
    return output_final

def _postprocess_audio(output_audio, original_length):
    output_audio = output_audio[:int(original_length)]
    return output_audio

def BinauralRenderer(mono_audio_path: str, spatial_plan_json: str, output_path: str) -> Dict[str, str]:
    try:
        audio_data, sample_rate = sf.read(mono_audio_path)
        spatial_plan = json.loads(spatial_plan_json)
        output_audio, output_sr = make_asmr_audio(audio_data, sample_rate, spatial_plan)
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        sf.write(output_path, output_audio, output_sr)
        if not os.path.exists(output_path):
            raise IOError(f"Failed to write output file to {output_path}")
        return {"binaural_output_path": output_path}
    except Exception as e:
        logging.error(f"Binaural rendering failed: {e}", exc_info=True)
        return {"error": f"Binaural rendering failed: {str(e)}"}

if __name__ == '__main__':
    pass