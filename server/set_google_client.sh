#!/bin/sh
# Put (or replace) the Google OAuth client used for "Login with Google" on the ZipZap proxy server.
# The client ID is public; the secret is typed into the server's prompt, so it never shows on screen.
set -e
HOST="${1:-xver@185.84.160.168}"
ssh -t "$HOST" '
read -rp "Google OAuth Client ID: " id
read -rsp "Google OAuth Client secret (hidden): " secret; echo
[ -n "$id" ] && [ -n "$secret" ] || { echo "Both values are needed"; exit 1; }
sudo sed -i "/^GOOGLE_CLIENT_ID=/d;/^GOOGLE_CLIENT_SECRET=/d" /etc/zipzap-proxy.env
printf "GOOGLE_CLIENT_ID=%s\nGOOGLE_CLIENT_SECRET=%s\n" "$id" "$secret" | sudo tee -a /etc/zipzap-proxy.env >/dev/null
unset secret
sudo systemctl restart zipzap-proxy
sleep 2
systemctl is-active zipzap-proxy >/dev/null && echo "ZipZap proxy restarted with Google login"
'
