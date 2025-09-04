import os
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state
from ..tools.binaural_renderer import BinauralRenderer

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the ASMR agent."""
    wav_path = await inject_session_state("{wav_path}", readonly_ctx)
    spatial_plan_json = await inject_session_state("{spatial_plan_json}", readonly_ctx)

    # Define the output path for the final binaural audio
    output_dir = "asmr_gen_adk/output/audio"
    base_name = os.path.basename(wav_path)
    binaural_output_path = os.path.join(output_dir, f"binaural_{base_name}")

    return (
        "You are the final audio processing engineer. Your task is to render the binaural ASMR audio "
        "using the provided mono audio file and the spatial plan."
        "\n\n"
        "1. **Mono Audio Path:** `{wav_path}`"
        "2. **Spatial Plan JSON:** `{spatial_plan_json}`"
        "3. **Output Path:** `{binaural_output_path}`"
        "\n\n"
        "Use the `BinauralRenderer` tool to perform the rendering. "
        f"Call the tool with: `BinauralRenderer(mono_audio_path='{wav_path}', spatial_plan_json='''{spatial_plan_json}''', output_path='{binaural_output_path}')`"
        "\n\n"
        "Upon completion, output only the path to the final binaural audio file."
    )

asmr_agent = LlmAgent(
    name="asmr_agent",
    model="gemini-2.5-flash",
    description="Renders a mono audio file into a binaural ASMR WAV file.",
    instruction=_build_instruction,
    tools=[BinauralRenderer],
    output_key="binaural_output_path",
)
