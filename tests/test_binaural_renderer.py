import pytest
import numpy as np
import soundfile as sf
import json
import os

# `asmr_gen_adk`がPythonパスに含まれるように、プロジェクトルートからの相対パスを追加
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asmr_gen_adk.tools.binaural_renderer import make_asmr_audio, BinauralRenderer, TARGET_FS

# --- Test Case 1: make_asmr_audio ---

def test_make_asmr_audio_success():
    """
    Tests if make_asmr_audio runs without errors and returns the correct data format.
    """
    # 1. Generate dummy mono audio data (1 second of white noise)
    sample_rate = 24000
    duration_sec = 1
    audio_data = np.random.uniform(-0.5, 0.5, size=(sample_rate * duration_sec)).astype(np.float32)

    # 2. Define a simple spatial plan
    spatial_plan = [
        {"time": 0.0, "azimuth": -30, "elevation": 10, "distance": 1.0, "reverb_mix": 0.1},
        {"time": 0.5, "azimuth": 30, "elevation": 10, "distance": 1.0, "reverb_mix": 0.2},
        {"time": 1.0, "azimuth": 0, "elevation": 0, "distance": 0.8, "reverb_mix": 0.15},
    ]

    # 3. Call the function
    try:
        output_audio, output_sr = make_asmr_audio(audio_data, sample_rate, spatial_plan)
    except Exception as e:
        pytest.fail(f"make_asmr_audio raised an exception unexpectedly: {e}")

    # 4. Assertions
    assert isinstance(output_audio, np.ndarray), "Output audio should be a NumPy array"
    assert isinstance(output_sr, int), "Output sample rate should be an integer"
    assert output_audio.ndim == 2, "Output audio should be stereo (2 dimensions)"
    assert output_audio.shape[1] == 2, "Output audio should have 2 channels"
    assert output_sr == TARGET_FS, f"Output sample rate should be {TARGET_FS}"
    assert len(output_audio) > 0, "Output audio should not be empty"


# --- Test Case 2: BinauralRenderer (Tool Wrapper) ---

def test_binaural_renderer_tool_success(tmp_path):
    """
    Tests the full tool wrapper, including file I/O.
    """
    # 1. Create a temporary directory for I/O
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    # 2. Generate a dummy mono WAV file
    sample_rate = 24000
    duration_sec = 2
    input_audio_data = np.random.uniform(-0.5, 0.5, size=(sample_rate * duration_sec)).astype(np.float32)
    input_wav_path = input_dir / "mono_input.wav"
    sf.write(input_wav_path, input_audio_data, sample_rate)

    # 3. Create a dummy spatial plan JSON
    spatial_plan = [
        {"time": 0.0, "azimuth": 0, "elevation": 0, "distance": 1.0, "reverb_mix": 0.2},
        {"time": 2.0, "azimuth": 45, "elevation": -10, "distance": 1.5, "reverb_mix": 0.3},
    ]
    spatial_plan_json = json.dumps(spatial_plan)

    # 4. Define the output path
    output_wav_path = output_dir / "binaural_output.wav"

    # 5. Call the tool function
    result = BinauralRenderer(
        mono_audio_path=str(input_wav_path),
        spatial_plan_json=spatial_plan_json,
        output_path=str(output_wav_path)
    )

    # 6. Assertions
    assert os.path.exists(output_wav_path), "Output WAV file was not created"
    assert "binaural_output_path" in result, "Result dictionary is missing the output path key"
    assert result["binaural_output_path"] == str(output_wav_path), "Result path does not match expected output path"

    # Verify the output file content
    output_audio, output_sr = sf.read(output_wav_path)
    assert output_sr == TARGET_FS, f"Sample rate of the output file should be {TARGET_FS}"
    assert output_audio.ndim == 2, "Output WAV file is not stereo"
    assert output_audio.shape[1] == 2, "Output WAV file does not have 2 channels"
