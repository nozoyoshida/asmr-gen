from google.adk.agents import LlmAgent

from .agents.script_agent import script_agent
from .agents.tts_agent import tts_agent

root_agent = LlmAgent(
    name="asmr_gen_coordinator",
    model="gemini-2.5-flash",
    description=(
        "Coordinator for ASMR-GEN MVP. First create a concise Japanese ASMR script,"
        " then synthesize a WAV using the TTS agent."
    ),
    instruction=(
        "You coordinate two specialists:\n"
        "1) script_agent — generate a short ASMR script (no more than ~120 words / 30s).\n"
        "2) tts_agent — take the final script text and produce a single-speaker WAV.\n\n"
        "Flow:\n"
        "- Ask the user for a 'situation' if unclear.\n"
        "- Call script_agent first to produce the script text. Ensure it is plain text, no markdown.\n"
        "- Then call tts_agent with the final script text and a suggested voice name (e.g., 'Kore' or 'Puck').\n"
        "- Return the file path of the generated WAV.\n"
        "If an error happens in tts, report it and offer an alternative voice.\n"
    ),
    sub_agents=[script_agent, tts_agent],
)
