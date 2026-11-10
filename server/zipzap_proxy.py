"""ZipZap AI proxy: keeps the Gemini API key on the server and limits use per install, per IP and in total.

The app points the google-genai SDK at this server and sends its install token where the SDK
would send an API key. The proxy checks the daily limits, swaps in the real key and forwards
the request to Gemini. Only the standard library is used, so the server needs no pip installs.
"""
import datetime
import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PATH_RE = re.compile(r"^/(v1|v1beta)/models/([A-Za-z0-9.\-]+):generateContent$")  # SDK 3.x uses v1
TOKEN_RE = re.compile(r"^zz-[0-9a-f]{32}$")
MAX_BODY = 20 * 1024 * 1024
UPSTREAM_TIMEOUT = 120
THAI_TIME = datetime.timezone(datetime.timedelta(hours=7))  # Limits reset at midnight in Thailand


@dataclass
class Settings:
    api_key: str
    upstream: str = "https://generativelanguage.googleapis.com"
    host: str = "127.0.0.1"
    port: int = 8787
    db_path: str = "usage.db"
    per_install: int = 50
    per_ip: int = 150
    total: int = 1000
    allowed_models: frozenset = frozenset({"gemini-flash-lite-latest", "gemini-3.6-flash"})
    trust_forwarded_for: bool = True

    @classmethod
    def from_env(cls, env=os.environ):
        return cls(
            api_key=env.get("GEMINI_API_KEY", "").strip(),
            upstream=env.get("ZIPZAP_UPSTREAM", cls.upstream).rstrip("/"),
            host=env.get("ZIPZAP_HOST", cls.host),
            port=int(env.get("ZIPZAP_PORT", cls.port)),
            db_path=env.get("ZIPZAP_DB", os.path.join(env.get("STATE_DIRECTORY", "."), "usage.db")),
            per_install=int(env.get("ZIPZAP_LIMIT_PER_INSTALL", cls.per_install)),
            per_ip=int(env.get("ZIPZAP_LIMIT_PER_IP", cls.per_ip)),
            total=int(env.get("ZIPZAP_LIMIT_TOTAL", cls.total)),
        )


def today():
    return datetime.datetime.now(THAI_TIME).date().isoformat()


class UsageStore:
    """Daily request counts, kept in SQLite so they survive restarts."""

    def __init__(self, path):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS usage ("
                         "day TEXT, kind TEXT, who TEXT, count INTEGER, PRIMARY KEY (day, kind, who))")
        self._db.commit()

    def _count(self, day, kind, who):
        row = self._db.execute("SELECT count FROM usage WHERE day=? AND kind=? AND who=?",
                               (day, kind, who)).fetchone()
        return row[0] if row else 0

    def try_consume(self, day, install, ip, settings):
        """Count one request if every limit allows it. Returns (ok, message)."""
        checks = [("install", install, settings.per_install,
                   f"ใช้ ZipZap AI ครบ {settings.per_install} ครั้งของวันนี้แล้ว ใช้ได้อีกครั้งหลังเที่ยงคืน "
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
                self._db.execute("INSERT INTO usage VALUES (?, ?, ?, 1) ON CONFLICT(day, kind, who) "
                                 "DO UPDATE SET count = count + 1", (day, kind, who))
            self._db.commit()
        return True, ""

    def used(self, day, install):
        with self._lock:
            return self._count(day, "install", install)


def make_handler(settings, store):
    class ProxyHandler(BaseHTTPRequestHandler):
        server_version = "ZipZapProxy/1.0"

        def log_message(self, fmt, *args):
            pass  # Request paths and headers carry nothing worth logging; errors are logged explicitly

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
            token = self.headers.get("x-goog-api-key", "").strip()
            return token if TOKEN_RE.fullmatch(token) else None

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self._send_json(200, {"ok": True})
            elif path == "/v1/usage":
                token = self._token()
                if token is None:
                    self._error(401, "UNAUTHENTICATED", "ไม่พบรหัสเครื่อง ZipZap")
                    return
                used = store.used(today(), token)
                self._send_json(200, {"used": used, "limit": settings.per_install,
                                      "remaining": max(settings.per_install - used, 0)})
            else:
                self._error(404, "NOT_FOUND", "ไม่พบหน้านี้")

        def do_POST(self):
            match = PATH_RE.fullmatch(self.path.split("?", 1)[0])
            if not match or match.group(2) not in settings.allowed_models:
                self._error(404, "NOT_FOUND", "ZipZap AI ไม่รองรับคำขอนี้")
                return
            token = self._token()
            if token is None:
                self._error(401, "UNAUTHENTICATED", "ไม่พบรหัสเครื่อง ZipZap")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length <= 0 or length > MAX_BODY:
                self._error(413, "INVALID_ARGUMENT", "ไฟล์ใหญ่เกินกว่าที่ ZipZap AI รับได้ (20MB)")
                return
            body = self.rfile.read(length)

            ok, message = store.try_consume(today(), token, self._client_ip(), settings)
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
    store = store or UsageStore(settings.db_path)
    return ThreadingHTTPServer((settings.host, settings.port), make_handler(settings, store))


def main():
    settings = Settings.from_env()
    if not settings.api_key:
        raise SystemExit("GEMINI_API_KEY is not set (put it in /etc/zipzap-proxy.env)")
    server = make_server(settings)
    print(f"ZipZap proxy on {settings.host}:{settings.port}, limits {settings.per_install}/install, "
          f"{settings.per_ip}/IP, {settings.total}/day", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
