import numpy as np
import soundfile as sf

from pedalboard import Pedalboard, Reverb
import spaudiopy as sp
import json

def BinauralRenderer(mono_audio_path: str, spatial_plan_json: str, output_path: str) -> dict:
    """
    モノラル音声をバイノーラルASMR体験にレンダリングするツールです。

    モノラル音声ファイルを処理し、空間化プランを適用します。

    Args:
        mono_audio_path: 入力モノラル音声ファイルのパス。
        spatial_plan_json: 空間音響キーフレームを表すJSON文字列。
        output_path: 出力バイノーラル音声ファイルを保存するパス。

    Returns:
        出力ファイルへのパスまたはエラーを含む辞書。
    """
    try:
        # モノラル音声を読み込み
        audio_signal = sp.io.load_audio(mono_audio_path)
        mono_audio, fs = audio_signal.signal, audio_signal.fs
        if mono_audio.ndim > 1:
            mono_audio = mono_audio[:, 0]  # シングルチャンネルに変換

        # 空間化プランをパース
        spatial_plan = json.loads(spatial_plan_json)

        # HRTFデータを読み込み
        hrtf = sp.io.load_hrirs(fs=fs)

        # プランからキーフレーム信号を作成
        times = [k['time'] for k in spatial_plan]
        azimuths = np.array([k.get('azimuth', 0) for k in spatial_plan])
        elevations = np.array([k.get('elevation', 0) for k in spatial_plan])
        distances = np.array([k.get('distance', 1) for k in spatial_plan])
        reverb_mixes = np.array([k.get('reverb_mix', 0) for k in spatial_plan])

        # 音声の長さをプランのデュレーションに合わせる
        total_duration = times[-1]
        n_samples = int(total_duration * fs)
        t = np.linspace(0, total_duration, n_samples)
        if len(mono_audio) < n_samples:
            mono_audio = np.pad(mono_audio, (0, n_samples - len(mono_audio)))
        else:
            mono_audio = mono_audio[:n_samples]

        # キーフレームを補間してスムーズなトランジションを作成
        azi_interp = np.interp(t, times, azimuths)
        ele_interp = np.interp(t, times, elevations)
        dist_interp = np.interp(t, times, distances)
        reverb_interp = np.interp(t, times, reverb_mixes)

        # 距離に基づくゲインを適用（逆二乗の法則）
        gain = 1.0 / (dist_interp**2 + 1e-6)
        dry_signal = mono_audio * gain

        # ドライ信号のバイノーラルレンダリング
        binaural_dry = sp.process.binaural_rendering(
            sp.sig.AmbiBSignal(dry_signal[:, np.newaxis], fs=fs),
            azi_interp, ele_interp, hrtf=hrtf
        )

        # ウェット信号のリバーブ処理
        board = Pedalboard([Reverb(room_size=0.7, damping=0.5, wet_level=1.0, dry_level=0.0, width=1.0)])
        wet_signal_mono = board(dry_signal, sample_rate=fs)

        # モノラルのウェット信号をステレオに変換してドライ信号の形状に合わせる
        binaural_wet = np.tile(wet_signal_mono[:, np.newaxis], (1, 2))

        # 等価パワークロスフェードを使用してドライ信号とウェット信号を動的にミキシング
        mix_factor_stereo = np.tile(np.clip(reverb_interp, 0.0, 1.0)[:, np.newaxis], (1, 2))
        dry_gain = np.cos(mix_factor_stereo * np.pi / 2)
        wet_gain = np.sin(mix_factor_stereo * np.pi / 2)
        output_signal = binaural_dry * dry_gain + binaural_wet * wet_gain

        # 最終的なバイノーラル音声を正規化して保存
        output_signal /= np.max(np.abs(output_signal)) + 1e-8
        sf.write(output_path, output_signal, fs)

        return {"binaural_output_path": output_path}
    except Exception as e:
        return {"error": f"Binaural rendering failed: {str(e)}"}