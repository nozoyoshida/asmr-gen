import yaml
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state
from ..tools.tts import synthesize_tts

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the TTS agent with state injection."""

    # Use optional state injection so missing keys don't raise a KeyError.
    script_text = await inject_session_state("{script_text?}", readonly_ctx)
    if not script_text:
        raise ValueError("`script_text` not found in session state")

    primary_voice = config["tts"]["primary_voice"]
    fallback_voice = config["tts"]["fallback_voice"]

    return (
        "Use the tool to synthesize speech from the script below.\n\n"
        f"=== SCRIPT ===\n{script_text}\n"
        "==============\n\n"
        f"Call synthesize_tts(text={script_text}, voice_name='{primary_voice}'). "
        f"If it fails, retry with voice_name='{fallback_voice}'. Return only the file path."
    )

tts_agent = LlmAgent(
    name="tts_agent",
    model=config["models"]["tts_agent"],
    description="Synthesize a mono WAV from the prior script using Gemini TTS.",
    instruction=_build_instruction,
    tools=[synthesize_tts],
    output_key="wav_path",
)
