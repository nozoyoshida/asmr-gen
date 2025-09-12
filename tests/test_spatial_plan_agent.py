import pytest
import json
from unittest.mock import AsyncMock, patch
from asmr_gen_adk.agents.spatial_plan_agent import _build_instruction

@pytest.mark.asyncio
async def test_build_instruction_spatial_plan():
    """
    Tests the prompt generation for the spatial_plan_agent.
    """
    # --- Setup ---
    mock_context = AsyncMock()
    test_wav_path = "/path/to/audio.wav"
    test_timed_script = {
        "scene_elements": [
            {
                "speaker": "main character",
                "script": "テスト用のセリフです。",
                "start_time": 0.5,
                "end_time": 3.2
            }
        ]
    }
    test_timed_script_json = json.dumps(test_timed_script, indent=2)

    # --- Mock inject_session_state ---
    async def mock_inject_side_effect(key, ctx):
        if key == "{timed_script_json}":
            return test_timed_script_json
        if key == "{wav_path}":
            return test_wav_path
        return None

    with patch('asmr_gen_adk.agents.spatial_plan_agent.inject_session_state', new_callable=AsyncMock) as mock_inject:
        mock_inject.side_effect = mock_inject_side_effect
        
        # --- Execute ---
        prompt = await _build_instruction(mock_context)
        
        # --- Assert ---
        assert mock_inject.call_count == 2
        mock_inject.assert_any_call("{timed_script_json}", mock_context)
        mock_inject.assert_any_call("{wav_path}", mock_context)
        
        # Check that the prompt contains the injected values, as it uses f-string formatting
        assert test_wav_path in prompt
        assert test_timed_script_json in prompt
        assert "keyframes" in prompt
        assert "azimuth" in prompt
        assert "elevation" in prompt
