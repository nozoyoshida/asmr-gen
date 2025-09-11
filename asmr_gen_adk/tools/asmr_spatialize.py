#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ASMR Spatializer (lightweight, HRTF-less)
- spatial_plan の keyframes を線形補間して、左右パン・距離・仰角・リバーブを時間変化させる
- HRTF は使わず、定電力パン + 距離減衰 + 簡易 EQ（LPF/HPF）+ 時間可変リバーブMixで“ASMRらしさ”を再現
"""

import argparse
import json
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import soundfile as sf
import librosa
from pedalboard import Pedalboard, Reverb, LowpassFilter, HighpassFilter

# -----------------------------
# Data model
# -----------------------------

@dataclass
class Keyframe:
    time: float       # seconds
    azimuth: float    # degrees (-90 = left, +90 = right)  ※入力の -15..+15 もOK
    elevation: float  # degrees (下 -90, 上 +90 を想定・任意)
    distance: float   # meters-ish (相対), 0.2~0.6 など
    reverb_mix: float # 0..1

def load_spatial_plan(path: str) -> List[Keyframe]:
    with open(path, "r", encoding="utf-8") as f:
        arr = json.load(f)
    plan = []
    for x in arr:
        plan.append(Keyframe(
            time=float(x["time"]),
            azimuth=float(x["azimuth"]),
            elevation=float(x["elevation"]),
            distance=float(x["distance"]),
            reverb_mix=float(x["reverb_mix"]),
        ))
    plan.sort(key=lambda k: k.time)
    return plan

# -----------------------------
# Utilities: curves & smoothing
# -----------------------------

def build_automation_curves(
    plan: List[Keyframe],
    total_dur_sec: float,
    sr: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    各パラメタのサンプル単位カーブを線形補間で生成。
    足りない末尾は最後の値でホールド。
    """
    n = int(round(total_dur_sec * sr))
    t_samples = np.arange(n) / sr

    # 時刻と各値の配列
    times = np.array([k.time for k in plan], dtype=np.float64)
    azs   = np.array([k.azimuth for k in plan], dtype=np.float64)
    els   = np.array([k.elevation for k in plan], dtype=np.float64)
    dsts  = np.array([k.distance for k in plan], dtype=np.float64)
    rmx   = np.array([k.reverb_mix for k in plan], dtype=np.float64)

    # 最後のキーフレームが音の終わりより前なら、終端にホールド点を追加
    if times[-1] < total_dur_sec:
        times = np.concatenate([times, [total_dur_sec]])
        azs   = np.concatenate([azs,   [azs[-1]]])
        els   = np.concatenate([els,   [els[-1]]])
        dsts  = np.concatenate([dsts,  [dsts[-1]]])
        rmx   = np.concatenate([rmx,   [rmx[-1]]])

    # 線形補間
    az_curve  = np.interp(t_samples, times, azs)
    el_curve  = np.interp(t_samples, times, els)
    d_curve   = np.interp(t_samples, times, dsts)
    rv_curve  = np.interp(t_samples, times, rmx)

    # 微小スムージング（クリック回避）
    def smooth(x, win=256):
        if win <= 1:
            return x
        k = np.hanning(win)
        k /= k.sum()
        pad = win // 2
        xp = np.pad(x, (pad, pad), mode='edge')
        return np.convolve(xp, k, mode='same')[pad:-pad]

    az_curve = smooth(az_curve, win=1024)
    el_curve = smooth(el_curve, win=1024)
    d_curve  = smooth(d_curve,  win=1024)
    rv_curve = smooth(rv_curve, win=2048)

    return az_curve, el_curve, d_curve, rv_curve

# -----------------------------
# Core rendering
# -----------------------------

def constant_power_pan(mono: np.ndarray, pan_curve: np.ndarray) -> np.ndarray:
    """
    定電力パンニング
    pan_curve: [-1.0 .. +1.0]（-1 左 / +1 右）
    """
    n = len(mono)
    assert len(pan_curve) == n

    # left/right ゲイン
    # L = sqrt(0.5*(1 - p)), R = sqrt(0.5*(1 + p))
    left_gain  = np.sqrt(0.5 * (1.0 - pan_curve))
    right_gain = np.sqrt(0.5 * (1.0 - (-pan_curve)))  # = sqrt(0.5*(1+p))

    out = np.zeros((n, 2), dtype=np.float32)
    out[:, 0] = mono * left_gain
    out[:, 1] = mono * right_gain
    return out

def distance_attenuation(distance_curve: np.ndarray, k: float = 2.0) -> np.ndarray:
    """
    距離による減衰（簡易）：gain = 1 / (1 + k * d^2)
    """
    return 1.0 / (1.0 + k * (distance_curve ** 2))

def map_distance_to_lpf_cutoff(distance_curve: np.ndarray,
                               f_near=18000.0, f_far=8000.0) -> np.ndarray:
    """
    距離が遠いほどローパスのカットオフを下げる（直感的マッピング）
    """
    # 正規化 d in [d_min, d_max] → α in [0,1]
    d_min, d_max = np.min(distance_curve), np.max(distance_curve)
    if d_max - d_min < 1e-6:
        alpha = np.zeros_like(distance_curve)
    else:
        alpha = (distance_curve - d_min) / (d_max - d_min)
    return f_near * (1.0 - alpha) + f_far * alpha

def map_elevation_to_hpf_cutoff(elev_curve: np.ndarray,
                                f_low=20.0, f_high=200.0) -> np.ndarray:
    """
    仰角が上（+）ほど低域を少し整理（HPFを上げる）
    """
    # elev [-90..+90] を 0..1 へ
    e = np.clip((elev_curve + 90.0) / 180.0, 0.0, 1.0)
    return f_low * (1.0 - e) + f_high * e

def apply_time_varying_filters(
    stereo: np.ndarray,
    sr: int,
    lpf_cutoffs: np.ndarray,
    hpf_cutoffs: np.ndarray,
    step: int = 2048
) -> np.ndarray:
    """
    時間で変化する LPF/HPF をブロックごとに適用（クロスフェードで継ぎ目抑制）
    ※高品位な連続EQではないが軽量でクリックを避けられる
    """
    n = stereo.shape[0]
    out = np.zeros_like(stereo)
    board = Pedalboard()

    # ブロック処理時のクロスフェード長
    xf = min(step // 4, 1024)
    prev_tail = None

    for start in range(0, n, step):
        end = min(start + step, n)
        seg = stereo[start:end].astype(np.float32, copy=False)

        # そのブロックの代表値（中央値）でフィルタを作る
        lpf = float(np.median(lpf_cutoffs[start:end]))
        hpf = float(np.median(hpf_cutoffs[start:end]))

        chain = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=max(20.0, min(hpf, sr/2 - 100.0))),
            LowpassFilter(cutoff_frequency_hz=max(200.0, min(lpf, sr/2 - 100.0))),
        ])
        seg_f = chain(seg, sr)

        # クロスフェード合成
        if prev_tail is not None and xf > 0:
            fade = np.linspace(0.0, 1.0, xf, dtype=np.float32)[:, None]
            out[start:start+xf] = prev_tail * (1.0 - fade) + seg_f[:xf] * fade
            out[start+xf:end] = seg_f[xf:]
            prev_tail = seg_f[end - start - xf:]
        else:
            out[start:end] = seg_f
            prev_tail = seg_f[-xf:] if (end - start) >= xf else seg_f

    return out

def apply_time_varying_reverb_mix(
    dry: np.ndarray,
    sr: int,
    mix_curve: np.ndarray,
    reverb_params: dict = None,
    block: int = 48000
) -> np.ndarray:
    """
    pedalboard.Reverb で WET を一度まとめて生成 → sample ごとに dry/wet をブレンド
    reverb_params: {room_size, damping, wet_level, dry_level, width}
    実際のWet量は mix_curve に従う（wet_level はベース）
    """
    if reverb_params is None:
        reverb_params = dict(room_size=0.25, damping=0.25, wet_level=0.2, dry_level=0.0, width=1.0)

    # リバーブは線形なので、まとめてかけて OK
    rev = Reverb(**reverb_params)
    wet = rev(dry.astype(np.float32), sr)

    # ブロックごとにブレンド（長尺でもメモリ節約）
    n = dry.shape[0]
    out = np.empty_like(dry, dtype=np.float32)
    for start in range(0, n, block):
        end = min(start + block, n)
        m = mix_curve[start:end].astype(np.float32)[:, None]  # (B,1)
        out[start:end] = dry[start:end] * (1.0 - m) + wet[start:end] * m
    return out

# -----------------------------
# Main pipeline
# -----------------------------

def process(
    input_wav: str,
    plan_json: str,
    output_wav: str,
    target_sr: int = 48000,
    trim_silence_db: float = 20.0
):
    # 1) 読み込み（float32）
    audio, sr = sf.read(input_wav, dtype="float32", always_2d=False)
    # モノ化（librosa の to_mono は (n,2) ではなく (2,n) 想定なので転置注意）
    if audio.ndim == 2:
        audio_mono = librosa.to_mono(audio.T)
    else:
        audio_mono = audio

    # 2) リサンプル & 無音トリム
    if sr != target_sr:
        audio_mono = librosa.resample(audio_mono, orig_sr=sr, target_sr=target_sr, res_type="soxr_hq")
        sr = target_sr

    audio_mono, _ = librosa.effects.trim(audio_mono, top_db=trim_silence_db)

    # 3) プランのロード & カーブ生成
    plan = load_spatial_plan(plan_json)
    total_dur_sec = len(audio_mono) / sr
    az_curve, el_curve, dist_curve, rv_curve = build_automation_curves(plan, total_dur_sec, sr)

    # 4) パンニング（azimuth→pan in [-1,1] へ射影）
    #    ここでは azimuth_deg / 90 で単純射影。必要なら感度係数で調整。
    pan_curve = np.clip(az_curve / 90.0, -1.0, 1.0)
    stereo = constant_power_pan(audio_mono, pan_curve)

    # 5) 距離：ゲイン減衰 + LPF、仰角：HPF
    gain = distance_attenuation(dist_curve, k=2.0).astype(np.float32)
    stereo *= gain[:, None]

    lpf_cut = map_distance_to_lpf_cutoff(dist_curve, f_near=18000.0, f_far=8000.0)
    hpf_cut = map_elevation_to_hpf_cutoff(el_curve, f_low=20.0, f_high=200.0)

    stereo = apply_time_varying_filters(stereo, sr, lpf_cut, hpf_cut, step=4096)

    # 6) リバーブ（時間可変 Mix）
    # 近接感を壊さないよう、短め＆控えめの設定を既定に
    reverb_base = dict(room_size=0.15, damping=0.25, wet_level=0.3, dry_level=0.0, width=1.0)
    out = apply_time_varying_reverb_mix(stereo, sr, rv_curve, reverb_params=reverb_base, block=sr)

    # ソフトリミット的に軽く正規化（過大ピーク抑制）
    peak = np.max(np.abs(out))
    if peak > 0.99:
        out = out / (peak + 1e-9) * 0.98

    # 7) 書き出し
    sf.write(output_wav, out, sr, subtype="PCM_16")
    print(f"[OK] Wrote: {output_wav}  (sr={sr}, duration={len(out)/sr:.2f}s)")

# -----------------------------
# CLI
# -----------------------------

def main():
    p = argparse.ArgumentParser(description="Render ASMR-like spatial audio from mono WAV and spatial plan.")
    p.add_argument("--input", required=True, help="Input WAV (mono recommended; stereo will be averaged)")
    p.add_argument("--plan", required=True, help="Spatial plan JSON (array of keyframes)")
    p.add_argument("--output", required=True, help="Output WAV (stereo)")
    p.add_argument("--sr", type=int, default=48000, help="Target sample rate (default: 48000)")
    p.add_argument("--no-trim", action="store_true", help="Disable head/tail silence trim")
    args = p.parse_args()

    process(
        input_wav=args.input,
        plan_json=args.plan,
        output_wav=args.output,
        target_sr=args.sr,
        trim_silence_db=(999.0 if args.no_trim else 20.0)
    )

if __name__ == "__main__":
    main()
