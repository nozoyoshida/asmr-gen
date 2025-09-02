from google.adk.agents import LlmAgent
from ..tools.tts import synthesize_tts

tts_agent = LlmAgent(
    name="tts_agent",
    model="gemini-2.5-flash",
    description="Synthesizes a WAV from given text using Gemini TTS.",
    instruction=(
        "Use the tool synthesize_tts(text, wav_path, voice_name) to generate a WAV file. "
        "Default voice_name is 'Kore'. If it fails, try 'Puck'. "
        "Return the output path so the coordinator can present it to the user."
    ),
    tools=[synthesize_tts],
)
