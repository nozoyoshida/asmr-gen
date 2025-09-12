import pytest
from unittest.mock import AsyncMock, patch
from asmr_gen_adk.agents.jsonize_agent import _build_instruction

@pytest.mark.asyncio
async def test_build_instruction_jsonize():
    """
    Tests the prompt generation for the jsonize_agent.
    """
    # --- Setup ---
    mock_context = AsyncMock()
    test_wav_path = "/path/to/test.wav"
    test_script_text = "これはテスト用の脚本です。"
    
    # --- Mock inject_session_state ---
    # We need to mock the return values for two separate calls
    async def mock_inject_side_effect(key, ctx):
        if key == "{script_text}":
            return test_script_text
        if key == "{wav_path}":
            return test_wav_path
        return None

    with patch('asmr_gen_adk.agents.jsonize_agent.inject_session_state', new_callable=AsyncMock) as mock_inject:
        mock_inject.side_effect = mock_inject_side_effect
        
        # --- Execute ---
        prompt = await _build_instruction(mock_context)
        
        # --- Assert ---
        assert mock_inject.call_count == 2
        # Ensure inject_session_state was called with the correct keys
        mock_inject.assert_any_call("{script_text}", mock_context)
        mock_inject.assert_any_call("{wav_path}", mock_context)
        
        # Check that the returned prompt contains the placeholders
        assert "{wav_path}" in prompt
        assert "{script_text}" in prompt
        assert "scene_elements" in prompt
        assert "start_time" in prompt
        assert "end_time" in prompt
