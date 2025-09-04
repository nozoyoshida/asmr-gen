import os
import wave
import time
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Get the API key
try:
    api_key = os.environ["GEMINI_API_KEY"]
except KeyError:
    print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
    exit(1)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

JAPANESE_VOICES = [
    "zephyr", "puck", "charon", "kore", "fenrir", "leda", "orus", "aoede",
    "callirrhoe", "autonoe", "enceladus", "iapetus", "umbriel", "algieba",
    "despina", "erinome", "algenib", "rasalgethi", "laomedeia", "achernar",
    "alnilam", "schedar", "gacrux", "pulcherrima", "achird", "zubenelgenubi",
    "vindemiatrix", "sadachbia", "sadaltager", "sulafat"
]

def _save_wav(
    filename: str, pcm: bytes, ch: int = 1, rate: int = 24000, sw: int = 2
) -> str:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(sw)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return filename

def synthesize_all_samples():
    """Synthesizes speech for all Japanese voices and combines them into a single WAV file."""
    client = genai.Client(api_key=api_key)
    temp_files = []
    
    for voice_name in JAPANESE_VOICES:
        text = f"こんにちは、こちらが{voice_name}サンプルボイスです"
        print(f"Synthesizing for voice: {voice_name}")
        
        try:
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
            temp_path = os.path.join(AUDIO_DIR, f"temp_{voice_name}.wav")
            _save_wav(temp_path, data)
            temp_files.append(temp_path)
        except Exception as e:
            print(f"Error synthesizing for voice {voice_name}: {e}")
        
        time.sleep(1) # Avoid hitting rate limits

    # Combine all temporary WAV files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = os.path.join(AUDIO_DIR, f"all_samples_{timestamp}.wav")
    
    with wave.open(final_path, 'wb') as outfile:
        is_first_file = True
        for temp_path in temp_files:
            with wave.open(temp_path, 'rb') as infile:
                if is_first_file:
                    outfile.setparams(infile.getparams())
                    is_first_file = False
                
                # Add a short silence between samples
                silence_duration_ms = 500
                sample_rate = infile.getframerate()
                num_silence_samples = int(sample_rate * (silence_duration_ms / 1000.0))
                silence_frames = b'\x00\x00' * num_silence_samples # 16-bit stereo silence

                outfile.writeframes(infile.readframes(infile.getnframes()))
                outfile.writeframes(silence_frames)

            # Clean up temporary file
            os.remove(temp_path)
            
    print(f"Successfully created combined audio file: {final_path}")
    return {"wav_path": final_path}

if __name__ == "__main__":
    synthesize_all_samples()