from google.adk.agents import LlmAgent
from ..tools.tts import synthesize_tts

tts_agent = LlmAgent(
    name="tts_agent",
    model="gemini-2.5-flash",
    description="Synthesize a mono WAV from the prior script using Gemini TTS.",
    # state からスクリプト文字列を注入（{script_text}）
    instruction=(
        "Use the tool to synthesize speech from the script below.\n\n"
        "=== SCRIPT ===\n{script_text}\n"
        "==============\n\n"
        "Call synthesize_tts(text={script_text}, voice_name='Kore'). "
        "If it fails, retry with voice_name='Puck'. Return only the file path."
    ),
    tools=[synthesize_tts],
    output_key="wav_path",  # 生成先パスを state['wav_path'] に格納（次で参照しやすい）
)
