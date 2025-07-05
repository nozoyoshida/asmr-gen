#!/usr/bin/env python3
import os
import sys
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

def main():
    if len(sys.argv) < 2:
        text = input("テキストを入力: ")
    else:
        text = sys.argv[1]
    
    print(f"音声生成中: {text}")
    
    try:
        tts = gTTS(text=text, lang='ja')
        filename = f"speech_{len(text)}.mp3"
        tts.save(filename)
        print(f"✅ 完了: {filename}")
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()