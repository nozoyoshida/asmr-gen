## 実行したい時
### 起動
adk web -reload -v
adk run asmr_gen_adk

### シチュエーションを入力する
例：彼女と南国のホテルで


## 再起動した時
source /home/admin_/asmr-gen/.venv/bin/activate

## port 削除したい時
sudo apt-get update
sudo apt install lsof
lsof -i:8000
kill <port number>

## 必要ツールインストール
sudo apt-get install libportaudio2 portaudio19-dev

## gemini の TTS の女性リスト
zephyr
kore
leda
aoede
autonoe
Callirhoe
despina
erinome
laomedeia
achernar
vindemiatrix
sulafat

## token refresh 必要な時
/auth で認証し直す