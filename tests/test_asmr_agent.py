import pytest
import os
from unittest.mock import AsyncMock, patch

# `asmr_gen_adk`がPythonパスに含まれるように、プロジェクトルートからの相対パスを追加
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from asmr_gen_adk.agents.asmr_agent import _build_instruction

# --- Test Case 1: _build_instruction ---

@pytest.mark.asyncio
async def test_build_instruction_prompt_generation():
    """
    Tests that the prompt is correctly generated from session state,
    including JSON cleanup.
    """
    # 1. Define test data
    test_wav_path = "asmr_gen_adk/output/audio/output_20250912_123456.wav"
    test_spatial_plan = '[{"time": 0.0, "azimuth": 0, "distance": 1}]'
    
    # Test data with markdown that needs to be stripped
    test_spatial_plan_with_markdown = f"""
```json
{test_spatial_plan}
```"""

    # 2. Mock ReadonlyContext and inject_session_state
    mock_readonly_ctx = AsyncMock()

    # Use patch to mock the inject_session_state function within the asmr_agent module
    with patch('asmr_gen_adk.agents.asmr_agent.inject_session_state') as mock_inject:
        # Set up the mock to return different values based on the key it's called with
        mock_inject.side_effect = [
            test_wav_path,  # First call gets the wav_path
            test_spatial_plan_with_markdown  # Second call gets the spatial plan
        ]

        # 3. Call the function with the mocked context
        prompt = await _build_instruction(mock_readonly_ctx)

    # 4. Assertions
    
    # Check that inject_session_state was called correctly
    mock_inject.assert_any_call("{wav_path}", mock_readonly_ctx)
    mock_inject.assert_any_call("{spatial_plan_json}", mock_readonly_ctx)

    # Check that the wav_path is correctly embedded
    assert f"1. **Mono Audio Path:** `{test_wav_path}`" in prompt
    
    # Check that the spatial plan is correctly embedded AND the markdown is stripped
    # The agent wraps the JSON in triple quotes for the tool call
    cleaned_json = test_spatial_plan_with_markdown.strip().replace("```json", "").replace("```", "").strip()
    assert f"spatial_plan_json='''{cleaned_json}'''" in prompt
    assert "```json" not in prompt # Ensure markdown is gone

    # Check that the output path is correctly constructed and embedded
    base_name = os.path.basename(test_wav_path)
    expected_output_path = f"asmr_gen_adk/output/binaural_audio/binaural_{base_name}"
    assert f"3. **Output Path:** `{expected_output_path}`" in prompt
    
    # Check that the final tool call is well-formed
    expected_tool_call = (
        f"Call the tool with: `BinauralRenderer(mono_audio_path='{test_wav_path}', "
        f"spatial_plan_json='''{cleaned_json}''', "
        f"output_path='{expected_output_path}')`"
    )
    assert expected_tool_call in prompt
