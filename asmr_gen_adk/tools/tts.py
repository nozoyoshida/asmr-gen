import os
import wave
from google import genai
from google.genai import types

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_wav(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> str:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return filename

def synthesize_tts(text: str, wav_path: str = None, voice_name: str = "Kore") -> dict:
    if wav_path is None:
        wav_path = os.path.join(OUTPUT_DIR, "output.wav")

    try:
        client = genai.Client()
        resp = client.models.generate_content(
            model="gemini-2.5-pro-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            ),
        )
        data = resp.candidates[0].content.parts[0].inline_data.data
        save_wav(wav_path, data)
        return {"status": "success", "wav_path": wav_path}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
