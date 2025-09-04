import json
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the spatial plan agent."""
    situation = await inject_session_state("{situation}", readonly_ctx)
    script_json = await inject_session_state("{script_json}", readonly_ctx)
    wav_path = await inject_session_state("{wav_path}", readonly_ctx)

    # The prompt is in a separate file, but we pass the wav_path for context.
    # The model will use its multi-modal capabilities to analyze the audio.
    # We are also passing the script content explicitly in the prompt.
    return (
        "You are a professional sound designer specializing in ASMR. "
        "Your task is to create a spatial audio plan (as a JSON array of keyframes) "
        "based on the provided script and the timing of the accompanying audio file. "
        "Analyze the script for movement cues and the audio for pacing and pauses. "
        "The keyframes should create a natural and immersive experience."
        "\n\n"
        "## Input Script (JSON):"
        f"```json\n{script_json}\n```"
        "\n"
        "## Input Audio File Path (for timing reference):"
        f"{wav_path}"
        "\n\n"
        "## Output Format Requirements:"
        "- A JSON array of keyframe objects."
        "- Each keyframe: {time: float, azimuth: float, elevation: float, distance: float, reverb_mix: float}"
        "- The `time` of each keyframe must align with the events in the audio file."
        "- Output ONLY the JSON array."
        "\n\n"
        f"Now, create the spatial plan for the situation: **{situation}**"
    )

spatial_plan_agent = LlmAgent(
    name="spatial_plan_agent",
    model="gemini-2.5-pro", # Assuming this model has multi-modal capabilities
    description="Creates a spatial audio plan from a script and audio file.",
    instruction=_build_instruction,
    output_key="spatial_plan_json",
)
