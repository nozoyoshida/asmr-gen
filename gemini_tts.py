#!/usr/bin/env python3
import os
import sys
import base64
import wave
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY が設定されていません")
        return
    
    if len(sys.argv) < 2:
        text = input("テキストを入力: ")
    else:
        text = sys.argv[1]
    
    print(f"Gemini API で音声生成中: {text}")
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
        
        # セクシーで息づかいが多い音声スタイルのプロンプト
        styled_text = f"Say in a sultry, breathy, and seductive whisper with heavy breathing, soft sighs, and intimate pauses: {text}"
        
        payload = {
            "contents": [{"parts": [{"text": styled_text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": sys.argv[2] if len(sys.argv) > 2 else "Kore"
                        }
                    }
                }
            }
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and data['candidates']:
                audio_data = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
                audio_bytes = base64.b64decode(audio_data)
                
                # outputフォルダを作成
                output_dir = Path('output')
                output_dir.mkdir(exist_ok=True)
                
                voice_name = sys.argv[2] if len(sys.argv) > 2 else "Kore"
                filename = output_dir / f"gemini_{voice_name}_{len(text)}.wav"
                with wave.open(str(filename), 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(audio_bytes)
                
                print(f"✅ 完了: {filename}")
                return filename
            else:
                print("❌ 音声データが見つかりません")
        else:
            print(f"❌ API エラー: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()