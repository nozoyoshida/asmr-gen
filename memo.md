## port 削除したい時
sudo apt-get update
sudo apt install lsof
lsof -i:8000
kill <port number>