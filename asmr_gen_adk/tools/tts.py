import os
import wave
from typing import Optional
from google import genai
from google.genai import types
from datetime import datetime

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


def _save_wav(
    filename: str, pcm: bytes, ch: int = 1, rate: int = 24000, sw: int = 2
) -> str:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(sw)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return filename


def synthesize_tts(
    text: str, wav_path: Optional[str] = None, voice_name: str = "Leda"
) -> dict:
    if wav_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_path = os.path.join(AUDIO_DIR, f"output_{timestamp}.wav")
    client = genai.Client()
    resp = client.models.generate_content(
        model="gemini-2.5-pro-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        ),
    )
    data = resp.candidates[0].content.parts[0].inline_data.data
    _save_wav(wav_path, data)
    return {"wav_path": wav_path}