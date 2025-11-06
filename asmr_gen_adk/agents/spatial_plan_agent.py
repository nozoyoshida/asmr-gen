import json
import yaml
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the spatial plan agent."""
    script_json = await inject_session_state("{timed_script_json}", readonly_ctx)
    wav_path = await inject_session_state("{wav_path}", readonly_ctx)

    return (
        "You are a professional sound designer specializing in ASMR and binaural audio. "
        "Your task is to create a spatial audio plan (as a JSON array of keyframes) "
        "based on the provided script and the timing of the accompanying audio file. "
        "Analyze the script for movement cues and the audio for pacing and pauses."
        "\n\n"
        "## CRITICAL CONSTRAINTS FOR ASMR REALISM (MUST FOLLOW):"
        "1. **Extremely Close & Dry:** ASMR requires intimacy. Maintain a distance between **0.1m to 0.3m** for most of the time."
        "2. **Reverb is Forbidden:** `reverb_mix` MUST be typically **0.0**. Max allowed is **0.03** (only when distant). Never exceed 0.05."
        "3. **Stable Elevation:** Keep `elevation` strictly at **0 (ear level)** unless specific overhead actions occur. Do not move it randomly."
        "4. **Slow Movements:** Listeners become dizzy with fast moves. Azimuth changes should be gradual and slow (max 30 degrees/sec)."
        "5. **Pause = Stop:** When there is silence in the audio, hold the position (stay still)."
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
        "Now, create the spatial plan."
    )

spatial_plan_agent = LlmAgent(
    name="spatial_plan_agent",
    model=config["models"]["spatial_plan_agent"],
    description="Creates a spatial audio plan from a script and audio file.",
    instruction=_build_instruction,
    output_key="spatial_plan_json",
)