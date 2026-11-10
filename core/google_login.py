"""Google sign-in for ZipZap AI, using the loopback + PKCE flow Google recommends for desktop apps.

The browser sends the authorization code back to a one-shot server on 127.0.0.1. The code is then
handed to the ZipZap server, which holds the OAuth client secret, trades it with Google and
returns a ZipZap session token. The app never sees the client secret or a Google access token.
"""
import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
LOGIN_TIMEOUT = 180
REQUEST_TIMEOUT = 30

DONE_PAGE = ("<!doctype html><meta charset='utf-8'><title>ZipZap</title>"
             "<body style='font-family:sans-serif;text-align:center;padding-top:80px'>"
             "<h2>{title}</h2><p>{body}</p></body>")


class LoginError(Exception):
    """Sign-in did not finish; the message is shown to the user."""


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=")
    return verifier, challenge.decode("ascii")


class _CallbackServer(HTTPServer):
    result = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/":
            self.send_response(404)  # e.g. /favicon.ico; keep waiting for the real callback
            self.end_headers()
            return
        params = dict(urllib.parse.parse_qsl(parsed.query))
        self.server.result = params
        ok = "code" in params
        page = DONE_PAGE.format(
            title="Login สำเร็จ" if ok else "Login ไม่สำเร็จ",
            body="กลับไปที่โปรแกรม ZipZap ได้เลย ปิดหน้านี้ได้" if ok else "กลับไปที่ ZipZap แล้วลองใหม่อีกครั้ง")
        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read())["error"]["message"]
        except (ValueError, KeyError, TypeError, OSError):
            message = f"server ตอบกลับผิดพลาด ({e.code})"
        raise LoginError(message) from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LoginError("ติดต่อ server ของ ZipZap ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่") from e


def fetch_client_id(proxy_url):
    try:
        with urllib.request.urlopen(f"{proxy_url}/v1/login/config", timeout=REQUEST_TIMEOUT) as response:
            client_id = json.loads(response.read()).get("google_client_id", "")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LoginError("ติดต่อ server ของ ZipZap ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่") from e
    if not client_id:
        raise LoginError("server ของ ZipZap ยังไม่ได้เปิด login ด้วย Google")
    return client_id


def sign_in(proxy_url, open_browser=webbrowser.open, timeout=LOGIN_TIMEOUT):
    """Run the whole sign-in. Returns {"session", "email", "name"}; raises LoginError."""
    client_id = fetch_client_id(proxy_url)
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    server = _CallbackServer(("127.0.0.1", 0), _CallbackHandler)
    server.timeout = 1
    redirect_uri = f"http://127.0.0.1:{server.server_port}"
    try:
        url = AUTH_URL + "?" + urllib.parse.urlencode({
            "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
            "scope": "openid email profile", "code_challenge": challenge, "code_challenge_method": "S256",
            "state": state, "prompt": "select_account",
        })
        if not open_browser(url):
            raise LoginError("เปิด browser ไม่ได้")
        deadline = time.monotonic() + timeout
        while server.result is None and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    result = server.result
    if result is None:
        raise LoginError("รอ login นานเกินไป ลองใหม่อีกครั้ง")
    if result.get("state") != state:
        raise LoginError("login ไม่สำเร็จ (state ไม่ตรงกัน) ลองใหม่อีกครั้ง")
    if "code" not in result:
        raise LoginError("ยกเลิก login แล้ว" if result.get("error") == "access_denied" else "login ไม่สำเร็จ")

    reply = _post_json(f"{proxy_url}/v1/login",
                       {"code": result["code"], "code_verifier": verifier, "redirect_uri": redirect_uri})
    if not reply.get("session"):
        raise LoginError("login ไม่สำเร็จ")
    return reply


def sign_out(proxy_url, session):
    """Best effort: forget the session on the server too."""
    try:
        _post_json(f"{proxy_url}/v1/logout", {}, headers={"x-goog-api-key": session})
    except LoginError:
        pass
