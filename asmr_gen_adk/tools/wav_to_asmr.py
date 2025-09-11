import json
import numpy as np
import soundfile as sf
import spaudiopy as spa
from pedalboard import Pedalboard, Compressor, Reverb, Gain, HighpassFilter
from scipy.interpolate import interp1d
import librosa
import os
import argparse

# 処理のターゲットサンプルレート (HRTFデータと一致させるため48kHzを推奨)
TARGET_SAMPLE_RATE = 48000 

def load_audio_mono(file_path, sample_rate):
    """WAVファイルを読み込み、モノラル信号に変換・前処理する"""
    print(f"Loading audio: {file_path}")
    try:
        # librosaを使用して読み込み、リサンプリング、モノラル化を行う
        # バイノーラル処理はモノラル音源に対して行う
        audio, sr = librosa.load(file_path, sr=sample_rate, mono=True)
    except Exception as e:
        print(f"Error loading audio file: {e}")
        raise e

    # ASMR向け前処理: 微小な無音部分のトリミング (Doc 2.4)
    # top_db=30 は比較的静かな音も残す設定
    audio, _ = librosa.effects.trim(audio, top_db=30)
    
    return audio, sr

def load_spatial_plan(json_input):
    """JSON文字列またはファイルパスから空間プランをロードする"""
    try:
        if os.path.exists(json_input):
            with open(json_input, 'r') as f:
                plan = json.load(f)
        else:
            plan = json.loads(json_input)
        return plan
    except Exception as e:
        print(f"Error loading or decoding spatial plan: {e}")
        raise

def interpolate_trajectory(plan, num_samples, sample_rate):
    """JSONの空間プランを補間し、全サンプルに対応する軌跡データを生成する"""
    print("Interpolating trajectory...")
    
    times = np.array([p['time'] for p in plan])
    duration = num_samples / sample_rate
    # 補間対象の時間軸（全サンプルに対応）
    t_interp = np.linspace(0, duration, num_samples)

    trajectory = {}
    keys = ['azimuth', 'elevation', 'distance', 'reverb_mix']
    
    for key in keys:
        values = np.array([p[key] for p in plan])
        # 線形補間関数を作成 (範囲外は最初/最後の値で固定: fill_value)
        f_interp = interp1d(times, values, kind='linear', bounds_error=False, fill_value=(values[0], values[-1]))
        trajectory[key] = f_interp(t_interp)
        
    return trajectory

def apply_distance_attenuation(audio, trajectory):
    """距離に基づいた音量調整を適用し、近接感を演出する (Doc 1.1, 1.3)"""
    print("Applying distance attenuation...")
    
    distances = trajectory['distance']
    # ASMRの親密さを演出するための基準距離
    REF_DISTANCE = 0.3  # 0.3mを基準とする
    MAX_GAIN = 2.5      # 最大増幅率 (約+8dB)
    MIN_DISTANCE = 0.05 # ゼロ除算防止と過度な増幅防止
    
    # ゲイン計算 (簡易的な逆数モデル 1/d)
    gains = REF_DISTANCE / np.maximum(distances, MIN_DISTANCE)
    gains = np.clip(gains, 0, MAX_GAIN)
    
    # ゲインを適用 (サンプル単位)
    return audio * gains

def binaural_rendering(audio, trajectory, sample_rate):
    """spaudiopyを使用して軌跡に沿ったバイノーラルレンダリングを行う (Doc 4章)"""
    print("Preparing HRTFs (Download may occur on first run)...")
    
    # 1. HRTFデータベースのロード
    try:
        # サンプルレートに合ったHRIRをロード
        hrirs = spa.IO.load_hrirs(fs=sample_rate)
    except Exception as e:
        print(f"Error loading HRIRs for sample rate {sample_rate}Hz. Check internet connection. Error: {e}")
        raise e

    print("Starting binaural rendering (This may take some time)...")
    
    # 2. 座標変換とレンダリング
    # spaudiopyは方位角(Azimuth)と天頂角(Colatitude: 90 - Elevation)を使用する
    azi = trajectory['azimuth']
    # 仰角(Elevation)を天頂角に変換
    elevation_clipped = np.clip(trajectory['elevation'], -90, 90)
    colat = 90 - elevation_clipped
    
    # 動的なバイノーラルレンダリングを実行
    # binauralize_spat は、時間変化する軌跡に対して効率的に畳み込みを行う
    binaural_audio = spa.process.binauralize_spat(audio, azi, colat, hrirs)
    
    print("Binaural rendering finished.")
    return binaural_audio

def apply_dynamic_effects(audio, trajectory, sample_rate):
    """Pedalboardを使用して動的なエフェクトを適用する (Doc 1.2, 3.1)"""
    print("Applying dynamic effects (Pedalboard)...")

    # 1. エフェクトの初期化
    # 低域ノイズ除去
    hpf = HighpassFilter(cutoff_frequency_hz=60)
    # ASMR向けの穏やかなコンプレッサー設定: 静かな部分を持ち上げつつ、ピークを抑える
    compressor = Compressor(threshold_db=-25, ratio=3, attack_ms=10, release_ms=150)
    # 親密で小さな空間をシミュレートするリバーブ
    reverb = Reverb(room_size=0.3, damping=0.7, width=0.8)
    
    board = Pedalboard([hpf, compressor, reverb])

    # 2. 動的処理 (reverb_mixの時間変化に対応)
    # パラメータ変更のため、ブロック単位で処理する
    block_size = 2048
    num_samples = len(audio)
    output_audio = np.zeros_like(audio)
    reverb_mix_traj = trajectory['reverb_mix']

    for start_idx in range(0, num_samples, block_size):
        end_idx = min(start_idx + block_size, num_samples)
        block = audio[start_idx:end_idx]
        
        # このブロックの平均リバーブミックス量を取得し、パラメータを更新
        current_reverb_mix = np.mean(reverb_mix_traj[start_idx:end_idx])
        reverb.wet_level = current_reverb_mix
        # 簡易的な線形クロスフェード
        reverb.dry_level = 1.0 - current_reverb_mix
        
        # エフェクト処理を実行
        processed_block = board.process(block, sample_rate)
        output_audio[start_idx:end_idx] = processed_block

    return output_audio

def process_wav_to_asmr(input_wav, output_wav, spatial_plan_input):
    """メイン処理関数"""
    
    # 1. 空間プランのロード
    spatial_plan = load_spatial_plan(spatial_plan_input)

    # 2. オーディオのロードと前処理
    audio_mono, sr = load_audio_mono(input_wav, TARGET_SAMPLE_RATE)
    num_samples = len(audio_mono)

    # 3. 軌跡の補間
    trajectory = interpolate_trajectory(spatial_plan, num_samples, sr)

    # 4. 距離減衰の適用
    # 注: 距離減衰はバイノーラルレンダリングの前に行う
    audio_distanced = apply_distance_attenuation(audio_mono, trajectory)

    # 5. バイノーラルレンダリング
    binaural_audio = binaural_rendering(audio_distanced, trajectory, sr)
    
    # 6. 動的エフェクト処理 (ASMR化)
    # 注: エフェクト処理はバイノーラル化されたステレオ信号に対して行う
    final_audio = apply_dynamic_effects(binaural_audio, trajectory, sr)

    # 7. 書き出し (Doc 2.2)
    print(f"Saving output audio to: {output_wav}")
    # クリッピング防止のため、ピーク値をチェックして必要なら正規化
    max_val = np.max(np.abs(final_audio))
    if max_val > 1.0:
        print(f"Warning: Output audio peak exceeds 1.0 (Peak: {max_val:.2f}). Normalizing.")
        final_audio /= max_val
        
    sf.write(output_wav, final_audio, sr)
    print("Processing complete.")

# 提供された入力JSONデータ
INPUT_JSON_DATA = """
[
  {"time": 0.0, "azimuth": 15, "elevation": 10, "distance": 0.3, "reverb_mix": 0.2},
  {"time": 0.613, "azimuth": 10, "elevation": 10, "distance": 0.28, "reverb_mix": 0.2},
  {"time": 2.533, "azimuth": 5, "elevation": 8, "distance": 0.35, "reverb_mix": 0.22},
  {"time": 6.093, "azimuth": -10, "elevation": 10, "distance": 0.38, "reverb_mix": 0.22},
  {"time": 7.143, "azimuth": -15, "elevation": 12, "distance": 0.35, "reverb_mix": 0.2},
  {"time": 10.593, "azimuth": 0, "elevation": 5, "distance": 0.4, "reverb_mix": 0.25},
  {"time": 16.273, "azimuth": 5, "elevation": 8, "distance": 0.35, "reverb_mix": 0.25},
  {"time": 17.203, "azimuth": -5, "elevation": 10, "distance": 0.25, "reverb_mix": 0.18},
  {"time": 20.483, "azimuth": 15, "elevation": 5, "distance": 0.3, "reverb_mix": 0.2},
  {"time": 23.403, "azimuth": 5, "elevation": 10, "distance": 0.2, "reverb_mix": 0.15},
  {"time": 26.833, "azimuth": 0, "elevation": 10, "distance": 0.2, "reverb_mix": 0.15}
]
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert WAV to immersive ASMR audio using a spatial plan.")
    parser.add_argument("-i", "--input_wav", help="Path to the input WAV file.", required=False)
    parser.add_argument("-o", "--output_wav", help="Path for the output binaural WAV file.", default="output_asmr_3d.wav")
    parser.add_argument("-p", "--plan", help="Path to the spatial plan JSON file (optional, uses built-in plan if omitted).", required=False)
    
    args = parser.parse_args()

    input_wav = args.input_wav
    output_wav = args.output_wav
    
    # プランが指定されていない場合は組み込みのデータを使用
    spatial_plan_input = args.plan if args.plan else INPUT_JSON_DATA

    # 入力WAVが指定されていない場合、テスト用ダミーファイルを生成して使用
    if not input_wav:
        input_wav = "dummy_input_asmr_source.wav"
        if not os.path.exists(input_wav):
            print(f"Input WAV not specified. Creating dummy input file: {input_wav}")
            duration = 30
            sr = TARGET_SAMPLE_RATE
            # ささやき声やブラッシング音に近い広帯域ノイズを生成
            num_samples = int(sr * duration)
            data = np.random.uniform(-1, 1, size=num_samples) * 0.05
            # 簡易的なフィルタリングで高域を強調（ASMRトリガーの再現）
            try:
                from scipy.signal import butter, lfilter
                b, a = butter(1, 1500 / (sr / 2), btype='high')
                data = lfilter(b, a, data)
            except ImportError:
                print("Scipy not fully available, using raw noise.")
            sf.write(input_wav, data, sr)

    try:
        process_wav_to_asmr(input_wav, output_wav, spatial_plan_input)
    except Exception as e:
        print(f"\nAn error occurred during processing: {e}")
        import traceback
        traceback.print_exc()