import pytest
from unittest.mock import AsyncMock, patch
from asmr_gen_adk.agents.tts_agent import _build_instruction

@pytest.mark.asyncio
async def test_build_instruction_normal():
    """
    Tests the normal case for _build_instruction where script_text exists.
    """
    # --- Setup ---
    mock_context = AsyncMock()
    test_script = "これはテスト用の脚本です。"
    
    # --- Mock inject_session_state ---
    with patch('asmr_gen_adk.agents.tts_agent.inject_session_state', new_callable=AsyncMock) as mock_inject:
        mock_inject.return_value = test_script
        
        # --- Execute ---
        prompt = await _build_instruction(mock_context)
        
        # --- Assert ---
        mock_inject.assert_called_once_with("{script_text?}", mock_context)
        assert test_script in prompt
        assert "Call synthesize_tts(text=" in prompt
        assert "voice_name='Kore'" in prompt
        assert "retry with voice_name='Puck'" in prompt

@pytest.mark.asyncio
async def test_build_instruction_no_script_text():
    """
    Tests the error case for _build_instruction where script_text is missing.
    """
    # --- Setup ---
    mock_context = AsyncMock()
    
    # --- Mock inject_session_state to return None ---
    with patch('asmr_gen_adk.agents.tts_agent.inject_session_state', new_callable=AsyncMock) as mock_inject:
        mock_inject.return_value = None
        
        # --- Execute & Assert ---
        with pytest.raises(ValueError, match="`script_text` not found in session state"):
            await _build_instruction(mock_context)
            
        mock_inject.assert_called_once_with("{script_text?}", mock_context)
