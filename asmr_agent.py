import os
import json
import mimetypes
import struct
from typing import Dict, List

from google import genai
from google.genai import types
from pydub import AudioSegment, effects


SYSTEM_PROMPT = """# 指示
あなたはプロの脚本家です。この後に入力される物語の設定を参考に、脚本を生成してください。

# 注意事項
状況の解説をする situation explainer が 1 人、物語内で実際に話す main character が 1 人存在する。
それぞれは、会話の中で干渉しない。

# 出力形式
脚本は以下の JSON format でのみ出力すること。
{
  "situation": "sample situation",
  "scene_elements": [
    {
      "speaker": "situation explainer",
      "script": "sample situation explanation"
    },
    {
      "speaker": "main character",
      "script": "sample script"
    },
    {
      "speaker": "situation explainer",
      "script": "sample situation explanation"
    },
    {
      "speaker": "main character",
      "script": "sample script"
    }
  ]
}
"""


def generate_script(situation: str) -> Dict:
    """Generate a screenplay based on a user provided situation."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    prompt = f"{SYSTEM_PROMPT}\n# 物語の設定\n{situation}"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        response_mime_type="application/json",
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=contents, config=config
    )
    return json.loads(response.text)


def save_script(script: Dict) -> str:
    """Persist a screenplay to the scripts directory."""
    os.makedirs("scripts", exist_ok=True)
    index = len(os.listdir("scripts"))
    path = os.path.join("scripts", f"script_{index}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    return path


def generate_audio(script: Dict) -> str:
    """Generate speech audio from a screenplay."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    lines = [f"{e['speaker']}: {e['script']}" for e in script["scene_elements"]]
    text = script["situation"] + "\n" + "\n".join(lines)
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=text)])
    ]
    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker="situation explainer",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Puck"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="main character",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        ),
                    ),
                ]
            )
        ),
    )

    audio_buffer = b""
    mime_type = "audio/wav"
    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-pro-preview-tts",
        contents=contents,
        config=config,
    ):
        if (
            chunk.candidates
            and chunk.candidates[0].content
            and chunk.candidates[0].content.parts
        ):
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                audio_buffer += part.inline_data.data
                mime_type = part.inline_data.mime_type

    if not audio_buffer:
        raise RuntimeError("No audio returned from model")

    extension = mimetypes.guess_extension(mime_type) or ".wav"
    if extension != ".wav":
        audio_buffer = convert_to_wav(audio_buffer, mime_type)
        extension = ".wav"

    os.makedirs("audio", exist_ok=True)
    index = len([f for f in os.listdir("audio") if f.endswith(".wav")])
    path = os.path.join("audio", f"audio_{index}_mono{extension}")
    with open(path, "wb") as f:
        f.write(audio_buffer)
    return path


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> Dict[str, int | None]:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def asmrify(input_path: str) -> str:
    """Convert mono audio to a simple ASMR-style stereo track."""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1)
    left = audio.pan(-0.6)
    right = audio.pan(0.6)
    asmr_audio = left.overlay(right)
    asmr_audio = effects.normalize(asmr_audio)
    index = len([f for f in os.listdir("audio") if f.startswith("asmr_")])
    output_path = os.path.join("audio", f"asmr_{index}.wav")
    asmr_audio.export(output_path, format="wav")
    return output_path


def main():
    situation = input("シチュエーションを入力してください: ")
    script = generate_script(situation)
    script_path = save_script(script)
    print(f"スクリプトを {script_path} に保存しました。")
    audio_path = generate_audio(script)
    print(f"音声を {audio_path} に保存しました。")
    asmr_path = asmrify(audio_path)
    print(f"ASMR 音声を {asmr_path} に保存しました。")


if __name__ == "__main__":
    main()
