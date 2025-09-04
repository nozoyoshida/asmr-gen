import numpy as np
import soundfile as sf

from pedalboard import Pedalboard, Reverb
import spaudiopy as sp
import json

def BinauralRenderer(mono_audio_path: str, spatial_plan_json: str, output_path: str) -> dict:
    """
    A tool to render mono audio into a binaural ASMR experience.

    Processes a mono audio file and applies a spatialization plan.

    Args:
        mono_audio_path: Path to the input mono audio file.
        spatial_plan_json: A JSON string representing the spatial audio keyframes.
        output_path: Path to save the output binaural audio file.

    Returns:
        A dictionary containing the path to the output file or an error.
    """
        try:
        # Load mono audio
        mono_audio, fs = sp.io.read_audio(mono_audio_path)
        if mono_audio.ndim > 1:
            mono_audio = mono_audio[:, 0]  # Ensure single channel

        # Parse the spatial plan
        spatial_plan = json.loads(spatial_plan_json)

        # Load HRTF data
        hrtf = sp.io.load_hrirs(samplerate=fs)

        # Create keyframe signals from the plan
        times = [k['time'] for k in spatial_plan]
        azimuths = np.array([k.get('azimuth', 0) for k in spatial_plan])
        elevations = np.array([k.get('elevation', 0) for k in spatial_plan])
        distances = np.array([k.get('distance', 1) for k in spatial_plan])
        reverb_mixes = np.array([k.get('reverb_mix', 0) for k in spatial_plan])

        # Ensure audio length matches the plan's duration
        total_duration = times[-1]
        n_samples = int(total_duration * fs)
        t = np.linspace(0, total_duration, n_samples)
        if len(mono_audio) < n_samples:
            mono_audio = np.pad(mono_audio, (0, n_samples - len(mono_audio)))
        else:
            mono_audio = mono_audio[:n_samples]

        # Interpolate keyframes to get smooth transitions
        azi_interp = np.interp(t, times, azimuths)
        ele_interp = np.interp(t, times, elevations)
        dist_interp = np.interp(t, times, distances)
        reverb_interp = np.interp(t, times, reverb_mixes)

        # Apply distance-based gain (inverse-square law)
        gain = 1.0 / (dist_interp**2 + 1e-6)
        dry_signal = mono_audio * gain

        # Binaural rendering for the dry signal
        binaural_dry = sp.process.binaural_rendering(
            sp.sig.AmbiBSignal(dry_signal[:, np.newaxis], fs=fs), 
            azi_interp, ele_interp, hrtf=hrtf
        )

        # Reverb processing for the wet signal
        board = Pedalboard([Reverb(room_size=0.7, damping=0.5, wet_level=1.0, dry_level=0.0, width=1.0)])
        wet_signal_mono = board(dry_signal, sample_rate=fs)
        
        # Convert mono wet signal to stereo to match dry signal shape
        binaural_wet = np.tile(wet_signal_mono[:, np.newaxis], (1, 2))

        # Dynamic mixing of dry and wet signals using equal-power crossfade
        mix_factor_stereo = np.tile(np.clip(reverb_interp, 0.0, 1.0)[:, np.newaxis], (1, 2))
        dry_gain = np.cos(mix_factor_stereo * np.pi / 2)
        wet_gain = np.sin(mix_factor_stereo * np.pi / 2)
        output_signal = binaural_dry * dry_gain + binaural_wet * wet_gain

        # Normalize and save the final binaural audio
        output_signal /= np.max(np.abs(output_signal)) + 1e-8
        sf.write(output_path, output_signal, fs)

        return {"binaural_output_path": output_path}
    except Exception as e:
        return {"error": f"Binaural rendering failed: {str(e)}"}
