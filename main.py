#!/usr/bin/env python3
"""
Gemini API TTS (Text-to-Speech) Program
Converts text to speech using Google's Gemini API
"""

import os
import sys
import base64
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Available voices (30 voices as per Gemini API documentation)
AVAILABLE_VOICES = [
    'Zephyr', 'Puck', 'Charon', 'Kore', 'Fenrir', 'Leda', 'Orus', 'Aoede',
    'Callirrhoe', 'Autonoe', 'Enceladus', 'Iapetus', 'Umbriel', 'Algieba',
    'Despina', 'Erinome', 'Algenib', 'Rasalgethi', 'Laomedeia', 'Achernar',
    'Alnilam', 'Schedar', 'Gacrux', 'Pulcherrima', 'Achird', 'Zubenelgenubi',
    'Vindemiatrix', 'Sadachbia', 'Sadaltager', 'Sulafat'
]

class GeminiTTS:
    def __init__(self, api_key: str):
        """Initialize Gemini TTS client"""
        self.client = genai.Client(api_key=api_key)
        self.output_dir = Path(os.getenv('OUTPUT_DIR', './output'))
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_speech(self, text: str, voice: str = 'Zephyr') -> bytes:
        """Generate speech from text using Gemini API"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice,
                            )
                        )
                    ),
                )
            )
            
            if not response.candidates:
                raise Exception("No response candidates received from API")
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise Exception("No content parts received from API")
            
            part = candidate.content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                raise Exception("No inline data found in response")
            
            if not part.inline_data.data:
                raise Exception("No audio data found in response")
            
            return part.inline_data.data
            
        except Exception as e:
            raise Exception(f"Failed to generate speech: {str(e)}")
    
    def save_audio(self, audio_data: bytes, filename: Optional[str] = None) -> Path:
        """Save audio data to WAV file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"speech_{timestamp}.wav"
        
        if not filename.endswith('.wav'):
            filename += '.wav'
        
        output_path = self.output_dir / filename
        
        try:
            self._write_wave_file(str(output_path), audio_data)
            return output_path
        except Exception as e:
            raise Exception(f"Failed to save audio file: {str(e)}")
    
    def _write_wave_file(self, filename: str, pcm_data: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2):
        """Write PCM data to WAV file with proper headers"""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)

def validate_voice(voice: str) -> str:
    """Validate voice selection"""
    if voice not in AVAILABLE_VOICES:
        available = ', '.join(AVAILABLE_VOICES[:5]) + f" (and {len(AVAILABLE_VOICES)-5} more)"
        raise click.BadParameter(f"Invalid voice '{voice}'. Available voices: {available}")
    return voice

def validate_api_key() -> str:
    """Validate API key from environment"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        click.echo("Error: GEMINI_API_KEY environment variable is required.", err=True)
        click.echo("Please set your API key in .env file or as environment variable.", err=True)
        sys.exit(1)
    return api_key

@click.command()
@click.argument('text', required=False)
@click.option('--voice', '-v', default=None, help='Voice to use for speech generation')
@click.option('--output', '-o', help='Output filename (without extension)')
@click.option('--list-voices', is_flag=True, help='List all available voices')
def main(text: Optional[str], voice: Optional[str], output: Optional[str], list_voices: bool):
    """
    Gemini API TTS - Convert text to speech using Google's Gemini API
    
    Examples:
    \b
        python main.py "Hello, world!"
        python main.py "こんにちは" --voice Zephyr
        python main.py "Test message" --output my_speech.wav
    """
    
    # List voices and exit
    if list_voices:
        click.echo("Available voices:")
        for i, voice_name in enumerate(AVAILABLE_VOICES, 1):
            click.echo(f"  {i:2d}. {voice_name}")
        return
    
    # Get default voice from environment or use Zephyr
    if voice is None:
        voice = os.getenv('DEFAULT_VOICE', 'Zephyr')
    
    # Validate voice
    try:
        voice = validate_voice(voice)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        return
    
    # Get text input
    if text is None:
        text = click.prompt("Enter text to convert to speech")
    
    if not text.strip():
        click.echo("Error: Text cannot be empty.", err=True)
        return
    
    # Validate API key
    api_key = validate_api_key()
    
    # Initialize TTS
    try:
        tts = GeminiTTS(api_key)
        click.echo(f"Generating speech with voice: {voice}")
        
        # Generate speech
        audio_data = tts.generate_speech(text, voice)
        
        # Save audio file
        output_path = tts.save_audio(audio_data, output)
        
        click.echo(f"✅ Speech generated successfully!")
        click.echo(f"📁 Saved to: {output_path}")
        click.echo(f"📝 Text: {text[:50]}{'...' if len(text) > 50 else ''}")
        click.echo(f"🎤 Voice: {voice}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()