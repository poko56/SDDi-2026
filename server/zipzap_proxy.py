"""ZipZap AI proxy: keeps the Gemini API key on the server and limits use per Google account, per IP and in total.

Users sign in with Google. The app sends the authorization code it got from Google to /v1/login;
the proxy (which holds the OAuth client secret) exchanges it with Google, reads the verified
account from the ID token and issues its own session token. The app then points the google-genai
SDK at this server and sends the session token where the SDK would send an API key; the proxy
checks the daily limits, swaps in the real key and forwards the request to Gemini.
Only the standard library is used, so the server needs no pip installs.
"""
import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH_RE = re.compile(r"^/(v1|v1beta)/models/([A-Za-z0-9.\-]+):generateContent$")  # SDK 3.x uses v1
SESSION_RE = re.compile(r"^zs-[0-9a-f]{64}$")
OLD_INSTALL_TOKEN_RE = re.compile(r"^zz-[0-9a-f]{32}$")  # v1.1.0 apps, before Google sign-in
LOOPBACK_REDIRECT_RE = re.compile(r"^http://127\.0\.0\.1:\d{1,5}$")
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
MAX_BODY = 20 * 1024 * 1024
MAX_LOGIN_BODY = 8 * 1024
UPSTREAM_TIMEOUT = 120
THAI_TIME = datetime.timezone(datetime.timedelta(hours=7))  # Limits reset at midnight in Thailand

MSG_UPDATE_APP = "ZipZap AI ต้อง login ด้วย Google แล้ว กรุณาอัปเดตแอปเป็นเวอร์ชันล่าสุด"
MSG_LOGIN_AGAIN = "login หมดอายุหรือไม่ถูกต้อง กรุณา login ด้วย Google ใหม่ในหน้า Settings"
MSG_LOGIN_FAILED = "login ด้วย Google ไม่สำเร็จ ลองใหม่อีกครั้ง"


@dataclass
class Settings:
    api_key: str
    google_client_id: str = ""
    google_client_secret: str = ""
    upstream: str = "https://generativelanguage.googleapis.com"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    host: str = "127.0.0.1"
    port: int = 8787
    db_path: str = "usage.db"
    per_user: int = 50
    per_ip: int = 150
    total: int = 1000
    logins_per_ip: int = 30
    session_days: int = 30
    allowed_models: frozenset = frozenset({"gemini-flash-lite-latest", "gemini-3.6-flash"})
    trust_forwarded_for: bool = True

    @classmethod
    def from_env(cls, env=os.environ):
        per_user = env.get("ZIPZAP_LIMIT_PER_USER") or env.get("ZIPZAP_LIMIT_PER_INSTALL") or cls.per_user
        return cls(
            api_key=env.get("GEMINI_API_KEY", "").strip(),
            google_client_id=env.get("GOOGLE_CLIENT_ID", "").strip(),
            google_client_secret=env.get("GOOGLE_CLIENT_SECRET", "").strip(),
            upstream=env.get("ZIPZAP_UPSTREAM", cls.upstream).rstrip("/"),
            google_token_url=env.get("ZIPZAP_GOOGLE_TOKEN_URL", cls.google_token_url),
            host=env.get("ZIPZAP_HOST", cls.host),
            port=int(env.get("ZIPZAP_PORT", cls.port)),
            db_path=env.get("ZIPZAP_DB", os.path.join(env.get("STATE_DIRECTORY", "."), "usage.db")),
            per_user=int(per_user),
            per_ip=int(env.get("ZIPZAP_LIMIT_PER_IP", cls.per_ip)),
            total=int(env.get("ZIPZAP_LIMIT_TOTAL", cls.total)),
        )


def today():
    return datetime.datetime.now(THAI_TIME).date().isoformat()


def _hash(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class Store:
    """Daily request counts and login sessions, kept in SQLite so they survive restarts.

    Only a hash of each session token is stored, so a copy of the database cannot be used to log in.
    """

    def __init__(self, path):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS usage ("
                         "day TEXT, kind TEXT, who TEXT, count INTEGER, PRIMARY KEY (day, kind, who))")
        self._db.execute("CREATE TABLE IF NOT EXISTS sessions ("
                         "token_hash TEXT PRIMARY KEY, sub TEXT, email TEXT, name TEXT, expires REAL)")
        self._db.commit()

    def _count(self, day, kind, who):
        row = self._db.execute("SELECT count FROM usage WHERE day=? AND kind=? AND who=?",
                               (day, kind, who)).fetchone()
        return row[0] if row else 0

    def _add(self, day, kind, who):
        self._db.execute("INSERT INTO usage VALUES (?, ?, ?, 1) ON CONFLICT(day, kind, who) "
                         "DO UPDATE SET count = count + 1", (day, kind, who))

    def try_consume(self, day, user, ip, settings):
        """Count one AI request if every limit allows it. Returns (ok, message)."""
        checks = [("user", user, settings.per_user,
                   f"ใช้ ZipZap AI ครบ {settings.per_user} ครั้งของวันนี้แล้ว ใช้ได้อีกครั้งหลังเที่ยงคืน "
                   "หรือใส่ Gemini API Key ของตัวเองในหน้า Settings"),
                  ("ip", ip, settings.per_ip,
                   "เครือข่ายนี้ใช้ ZipZap AI ครบโควตาของวันนี้แล้ว ลองใหม่พรุ่งนี้"),
                  ("total", "all", settings.total,
                   "ZipZap AI ถูกใช้ครบโควตารวมของวันนี้แล้ว ลองใหม่พรุ่งนี้ หรือใส่ Gemini API Key ของตัวเอง")]
        with self._lock:
            for kind, who, limit, message in checks:
                if self._count(day, kind, who) >= limit:
                    return False, message
            for kind, who, _, _ in checks:
                self._add(day, kind, who)
            self._db.commit()
        return True, ""

    def try_login_attempt(self, day, ip, limit):
        with self._lock:
            if self._count(day, "login", ip) >= limit:
                return False
            self._add(day, "login", ip)
            self._db.commit()
        return True

    def used(self, day, user):
        with self._lock:
            return self._count(day, "user", user)

    def create_session(self, sub, email, name, days):
        token = "zs-" + secrets.token_hex(32)
        with self._lock:
            self._db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
            self._db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                             (_hash(token), sub, email, name, time.time() + days * 86400))
            self._db.commit()
        return token

    def session(self, token):
        """{"sub", "email", "name"} for a live session token, else None."""
        with self._lock:
            row = self._db.execute("SELECT sub, email, name, expires FROM sessions WHERE token_hash=?",
                                   (_hash(token),)).fetchone()
        if row is None or row[3] < time.time():
            return None
        return {"sub": row[0], "email": row[1], "name": row[2]}

    def delete_session(self, token):
        with self._lock:
            self._db.execute("DELETE FROM sessions WHERE token_hash=?", (_hash(token),))
            self._db.commit()


def _id_token_claims(id_token):
    """Payload of an ID token received straight from Google's token endpoint over TLS.

    Google's guidance is that a token obtained this way needs no signature check; its
    audience, issuer and expiry are still checked by the caller.
    """
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError):
        return None


def exchange_google_code(settings, code, code_verifier, redirect_uri):
    """Trade the authorization code for the user's verified Google identity, or return None."""
    form = urllib.parse.urlencode({
        "code": code, "code_verifier": code_verifier, "redirect_uri": redirect_uri,
        "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
        "grant_type": "authorization_code",
    }).encode("ascii")
    request = urllib.request.Request(settings.google_token_url, data=form, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            tokens = json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"google token exchange failed: {e.code}", flush=True)
        return None
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"google token exchange unreachable: {e}", flush=True)
        return None
    claims = _id_token_claims(tokens.get("id_token", ""))
    if (not claims or claims.get("aud") != settings.google_client_id or claims.get("iss") not in GOOGLE_ISSUERS
            or claims.get("exp", 0) < time.time() or not claims.get("sub")
            or claims.get("email_verified") is not True):
        print("google id token rejected", flush=True)
        return None
    return {"sub": claims["sub"], "email": claims.get("email", ""), "name": claims.get("name", "")}


def make_handler(settings, store):
    class ProxyHandler(BaseHTTPRequestHandler):
        server_version = "ZipZapProxy/2.0"

        def log_message(self, fmt, *args):
            pass  # Paths and headers carry tokens; errors are logged explicitly instead

        def _send_json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, code, status, message):
            self._send_json(code, {"error": {"code": code, "message": message, "status": status}})

        def _client_ip(self):
            peer = self.client_address[0]
            forwarded = self.headers.get("X-Forwarded-For", "")
            if settings.trust_forwarded_for and peer in ("127.0.0.1", "::1") and forwarded:
                return forwarded.split(",")[-1].strip()  # The entry Caddy appended
            return peer

        def _token(self):
            return self.headers.get("x-goog-api-key", "").strip()

        def _session(self):
            """The signed-in user, or None after sending a 401 that says what to do."""
            token = self._token()
            if OLD_INSTALL_TOKEN_RE.fullmatch(token):
                self._error(401, "UNAUTHENTICATED", MSG_UPDATE_APP)
                return None
            user = store.session(token) if SESSION_RE.fullmatch(token) else None
            if user is None:
                self._error(401, "UNAUTHENTICATED", MSG_LOGIN_AGAIN)
            return user

        def _read_body(self, limit):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length <= 0 or length > limit:
                return None
            return self.rfile.read(length)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self._send_json(200, {"ok": True, "login": bool(settings.google_client_id)})
            elif path == "/v1/login/config":
                self._send_json(200, {"google_client_id": settings.google_client_id})
            elif path == "/v1/usage":
                user = self._session()
                if user is None:
                    return
                used = store.used(today(), user["sub"])
                self._send_json(200, {"used": used, "limit": settings.per_user,
                                      "remaining": max(settings.per_user - used, 0),
                                      "email": user["email"], "name": user["name"]})
            else:
                self._error(404, "NOT_FOUND", "ไม่พบหน้านี้")

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path == "/v1/login":
                self._login()
            elif path == "/v1/logout":
                token = self._token()
                if SESSION_RE.fullmatch(token):
                    store.delete_session(token)
                self._send_json(200, {"ok": True})
            else:
                self._generate(path)

        def _login(self):
            if not (settings.google_client_id and settings.google_client_secret):
                self._error(503, "UNAVAILABLE", "server ของ ZipZap ยังไม่ได้ตั้งค่า login ด้วย Google")
                return
            if not store.try_login_attempt(today(), self._client_ip(), settings.logins_per_ip):
                self._error(429, "RESOURCE_EXHAUSTED", "login บ่อยเกินไป ลองใหม่พรุ่งนี้")
                return
            body = self._read_body(MAX_LOGIN_BODY)
            try:
                data = json.loads(body) if body else {}
            except ValueError:
                data = {}
            code, verifier, redirect = data.get("code"), data.get("code_verifier"), data.get("redirect_uri")
            if not (isinstance(code, str) and isinstance(verifier, str) and isinstance(redirect, str)
                    and LOOPBACK_REDIRECT_RE.fullmatch(redirect)):
                self._error(400, "INVALID_ARGUMENT", MSG_LOGIN_FAILED)
                return
            user = exchange_google_code(settings, code, verifier, redirect)
            if user is None:
                self._error(401, "UNAUTHENTICATED", MSG_LOGIN_FAILED)
                return
            session = store.create_session(user["sub"], user["email"], user["name"], settings.session_days)
            print(f"login {user['email']}", flush=True)
            self._send_json(200, {"session": session, "email": user["email"], "name": user["name"]})

        def _generate(self, path):
            match = PATH_RE.fullmatch(path)
            if not match or match.group(2) not in settings.allowed_models:
                self._error(404, "NOT_FOUND", "ZipZap AI ไม่รองรับคำขอนี้")
                return
            user = self._session()
            if user is None:
                return
            body = self._read_body(MAX_BODY)
            if body is None:
                self._error(413, "INVALID_ARGUMENT", "ไฟล์ใหญ่เกินกว่าที่ ZipZap AI รับได้ (20MB)")
                return
            ok, message = store.try_consume(today(), user["sub"], self._client_ip(), settings)
            if not ok:
                self._error(429, "RESOURCE_EXHAUSTED", message)
                return
            self._forward(match.group(1), match.group(2), body)

        def _forward(self, version, model, body):
            request = urllib.request.Request(
                f"{settings.upstream}/{version}/models/{model}:generateContent", data=body, method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": settings.api_key})
            try:
                with urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT) as response:
                    code, payload = response.status, response.read()
            except urllib.error.HTTPError as e:
                code, payload = e.code, e.read()
                print(f"upstream error {code} for {model}", flush=True)
                if code in (400, 401, 403) and (b"API_KEY_INVALID" in payload or b"API key" in payload):
                    # The user has no key to fix: say the team's server is misconfigured instead
                    self._error(503, "UNAVAILABLE", "server ของ ZipZap ตั้งค่า Gemini key ไม่ถูกต้อง แจ้งทีมพัฒนา "
                                                    "หรือใส่ Gemini API Key ของตัวเองในหน้า Settings")
                    return
            except (urllib.error.URLError, OSError) as e:
                print(f"upstream unreachable: {e}", flush=True)
                self._error(502, "UNAVAILABLE", "ZipZap AI ติดต่อ Gemini ไม่ได้ชั่วคราว ลองใหม่อีกครั้ง")
                return
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return ProxyHandler


def make_server(settings, store=None):
    store = store or Store(settings.db_path)
    return ThreadingHTTPServer((settings.host, settings.port), make_handler(settings, store))


def main():
    settings = Settings.from_env()
    if not settings.api_key:
        raise SystemExit("GEMINI_API_KEY is not set (put it in /etc/zipzap-proxy.env)")
    server = make_server(settings)
    login = "on" if settings.google_client_id and settings.google_client_secret else "NOT CONFIGURED"
    print(f"ZipZap proxy on {settings.host}:{settings.port}, Google login {login}, limits "
          f"{settings.per_user}/account, {settings.per_ip}/IP, {settings.total}/day", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
