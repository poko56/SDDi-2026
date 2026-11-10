#!/bin/sh
# Put (or replace) the Gemini API key on the ZipZap proxy server.
# The key is typed into the server's prompt, so it never shows on screen or lands in shell history.
set -e
HOST="${1:-xver@185.84.160.168}"
ssh -t "$HOST" '
read -rsp "Paste the Gemini API key, then press Enter: " k; echo
[ -n "$k" ] || { echo "No key entered"; exit 1; }
sudo sed -i "/^GEMINI_API_KEY=/d" /etc/zipzap-proxy.env
printf "GEMINI_API_KEY=%s\n" "$k" | sudo tee -a /etc/zipzap-proxy.env >/dev/null
unset k
sudo systemctl restart zipzap-proxy
sleep 2
systemctl is-active zipzap-proxy >/dev/null && echo "ZipZap proxy is running with the new key"
'
