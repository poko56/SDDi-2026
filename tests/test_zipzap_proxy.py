import base64
import json
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import core.config
from core.google_login import LoginError, sign_in
from core.llm import AINotConfiguredError, AIServiceError, ZipZapCloudClient
from core.services import build_services
from server.zipzap_proxy import Settings, Store, make_server

REAL_KEY = "real-secret-key"
CLIENT_ID = "test-client.apps.googleusercontent.com"
CLIENT_SECRET = "test-client-secret"
GEN_PATH = "/v1beta/models/gemini-flash-lite-latest:generateContent"
LOOPBACK = "http://127.0.0.1:5555"


def id_token(**claims):
    def part(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()
    payload = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "exp": time.time() + 3600,
               "email_verified": True, **claims}
    return f"{part({'alg': 'RS256'})}.{part(payload)}.signature"


class FakeGoogle(BaseHTTPRequestHandler):
    """Gemini's generateContent and Google's OAuth token endpoint, on one local server."""

    gemini_requests = []
    token_requests = []
    reject_key = False
    accounts = {}  # authorization code -> ID token claims

    def log_message(self, *args):
        pass

    def _reply(self, code, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path == "/token":
            form = dict(urllib.parse.parse_qsl(body.decode()))
            FakeGoogle.token_requests.append(form)
            claims = FakeGoogle.accounts.get(form.get("code"))
            if claims is None or form.get("client_secret") != CLIENT_SECRET:
                self._reply(400, {"error": "invalid_grant"})
            else:
                self._reply(200, {"access_token": "ya29.x", "id_token": id_token(**claims)})
            return
        FakeGoogle.gemini_requests.append({"path": self.path, "key": self.headers.get("x-goog-api-key")})
        if FakeGoogle.reject_key:
            self._reply(400, {"error": {"code": 400, "message": "API key not valid.", "status": "INVALID_ARGUMENT",
                                        "details": [{"reason": "API_KEY_INVALID"}]}})
        else:
            self._reply(200, {"candidates": [{"content": {"role": "model", "parts": [{"text": "สวัสดี"}]}}]})


def start(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def google():
    FakeGoogle.gemini_requests = []
    FakeGoogle.token_requests = []
    FakeGoogle.reject_key = False
    FakeGoogle.accounts = {
        "code-a": {"sub": "user-a", "email": "a@example.com", "name": "A"},
        "code-a2": {"sub": "user-a", "email": "a@example.com", "name": "A"},
        "code-b": {"sub": "user-b", "email": "b@example.com", "name": "B"},
        "code-c": {"sub": "user-c", "email": "c@example.com", "name": "C"},
        "code-d": {"sub": "user-d", "email": "d@example.com", "name": "D"},
        "bad-aud": {"sub": "x", "email": "x@example.com", "aud": "someone-else"},
        "unverified": {"sub": "y", "email": "y@example.com", "email_verified": False},
    }
    server = start(ThreadingHTTPServer(("127.0.0.1", 0), FakeGoogle))
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def make_proxy(tmp_path, google, **overrides):
    options = dict(api_key=REAL_KEY, google_client_id=CLIENT_ID, google_client_secret=CLIENT_SECRET,
                   upstream=google, google_token_url=f"{google}/token", port=0,
                   db_path=str(tmp_path / "usage.db"), per_user=2, per_ip=3, total=4, trust_forwarded_for=False)
    options.update(overrides)
    settings = Settings(**options)
    return start(make_server(settings, Store(settings.db_path)))


@pytest.fixture
def proxy(tmp_path, google):
    server = make_proxy(tmp_path, google)
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def call(url, path=GEN_PATH, token=None, body=b'{"contents": []}', method="POST"):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["x-goog-api-key"] = token
    request = urllib.request.Request(url + path, data=body if method == "POST" else None,
                                     headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def login(proxy, code="code-a", redirect_uri=LOOPBACK):
    body = json.dumps({"code": code, "code_verifier": "v" * 50, "redirect_uri": redirect_uri}).encode()
    return call(proxy, path="/v1/login", body=body)


def session_for(proxy, code="code-a"):
    code_, reply = login(proxy, code)
    assert code_ == 200, reply
    return reply["session"]


# ---------- Proxy: sign-in and sessions ----------

def test_login_config_gives_the_public_client_id(proxy):
    assert call(proxy, path="/v1/login/config", method="GET") == (200, {"google_client_id": CLIENT_ID})


def test_login_returns_a_session_for_a_verified_google_account(proxy):
    code, reply = login(proxy)

    assert code == 200
    assert reply["email"] == "a@example.com"
    assert reply["session"].startswith("zs-")
    assert FakeGoogle.token_requests[0]["client_secret"] == CLIENT_SECRET  # Secret is added by the server


@pytest.mark.parametrize("code_, expected", [("wrong-code", 401), ("bad-aud", 401), ("unverified", 401)])
def test_login_rejects_bad_codes_and_untrusted_tokens(proxy, code_, expected):
    status, reply = login(proxy, code_)

    assert status == expected
    assert "session" not in reply


@pytest.mark.parametrize("redirect", ["https://evil.example", "http://localhost:5555", "http://127.0.0.1:5555/x"])
def test_login_only_accepts_loopback_redirects(proxy, redirect):
    assert login(proxy, redirect_uri=redirect)[0] == 400
    assert FakeGoogle.token_requests == []


def test_login_is_refused_when_server_has_no_google_client(tmp_path, google):
    server = make_proxy(tmp_path, google, google_client_id="", google_client_secret="")
    try:
        assert login(f"http://127.0.0.1:{server.server_port}")[0] == 503
    finally:
        server.shutdown()


def test_v110_install_tokens_are_told_to_update(proxy):
    code, reply = call(proxy, token="zz-" + "a" * 32)

    assert code == 401
    assert "อัปเดตแอป" in reply["error"]["message"]
    assert FakeGoogle.gemini_requests == []


@pytest.mark.parametrize("token", [None, "AIzaFakeKey", "zs-" + "0" * 64])
def test_rejects_missing_or_unknown_sessions(proxy, token):
    code, reply = call(proxy, token=token)

    assert code == 401
    assert "login" in reply["error"]["message"]


def test_logout_ends_the_session(proxy):
    session = session_for(proxy)
    assert call(proxy, path="/v1/logout", token=session, body=b"{}")[0] == 200

    assert call(proxy, token=session)[0] == 401


def test_expired_sessions_are_rejected(tmp_path):
    store = Store(str(tmp_path / "usage.db"))
    token = store.create_session("user-a", "a@example.com", "A", days=-1)

    assert store.session(token) is None


def test_only_a_hash_of_the_session_is_stored(tmp_path, google):
    server = make_proxy(tmp_path, google)
    session = session_for(f"http://127.0.0.1:{server.server_port}")
    server.shutdown()

    dump = "\n".join(sqlite3.connect(str(tmp_path / "usage.db")).iterdump())
    assert session not in dump


# ---------- Proxy: forwarding and limits ----------

def test_forwards_with_real_key_and_hides_the_session(proxy):
    code, reply = call(proxy, token=session_for(proxy))

    assert code == 200
    assert reply["candidates"][0]["content"]["parts"][0]["text"] == "สวัสดี"
    assert FakeGoogle.gemini_requests == [{"path": GEN_PATH, "key": REAL_KEY}]


@pytest.mark.parametrize("path", ["/v1beta/models/gemini-ultra:generateContent", "/v1beta/files"])
def test_only_forwards_allowed_models_and_endpoints(proxy, path):
    assert call(proxy, path=path, token=session_for(proxy))[0] == 404
    assert FakeGoogle.gemini_requests == []


def test_limit_follows_the_google_account_across_sessions(proxy):
    first, second = session_for(proxy, "code-a"), session_for(proxy, "code-a2")  # Same account, two logins

    assert call(proxy, token=first)[0] == 200
    assert call(proxy, token=second)[0] == 200
    code, reply = call(proxy, token=first)

    assert code == 429
    assert "ครบ 2 ครั้ง" in reply["error"]["message"]


def test_limits_each_ip(proxy):
    sessions = [session_for(proxy, c) for c in ("code-a", "code-b", "code-c", "code-d")]

    assert [call(proxy, token=s)[0] for s in sessions] == [200, 200, 200, 429]  # per_ip=3


def test_usage_reports_account_and_remaining(proxy):
    session = session_for(proxy)
    call(proxy, token=session)

    code, usage = call(proxy, path="/v1/usage", token=session, method="GET")
    assert code == 200
    assert usage == {"used": 1, "limit": 2, "remaining": 1, "email": "a@example.com", "name": "A"}


def test_rejects_empty_body(proxy):
    assert call(proxy, token=session_for(proxy), body=b"")[0] == 413


def test_bad_server_key_is_reported_as_a_server_problem(proxy):
    FakeGoogle.reject_key = True

    with pytest.raises(AIServiceError, match="server ของ ZipZap ตั้งค่า Gemini key ไม่ถูกต้อง"):
        ZipZapCloudClient(proxy, session_for(proxy)).generate("hi")


# ---------- App: sign-in flow ----------

def fake_browser(code="code-a", error=None, wrong_state=False):
    """Stands in for the user's browser: follows Google's redirect back to the app's loopback server."""
    opened = []

    def open_browser(url):
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        opened.append(query)
        params = {"state": "forged" if wrong_state else query["state"]}
        params.update({"error": error} if error else {"code": code})
        callback = query["redirect_uri"] + "/?" + urllib.parse.urlencode(params)
        threading.Thread(target=urllib.request.urlopen, args=(callback,), daemon=True).start()
        return True

    open_browser.opened = opened
    return open_browser


def test_sign_in_uses_pkce_and_returns_a_session(proxy):
    browser = fake_browser()
    result = sign_in(proxy, open_browser=browser, timeout=10)

    query = browser.opened[0]
    assert query["client_id"] == CLIENT_ID
    assert query["code_challenge_method"] == "S256" and query["code_challenge"]
    assert query["redirect_uri"].startswith("http://127.0.0.1:")
    assert result["email"] == "a@example.com"
    assert FakeGoogle.token_requests[0]["code_verifier"]  # The verifier travels to Google via the server


def test_sign_in_cancelled_in_browser(proxy):
    with pytest.raises(LoginError, match="ยกเลิก"):
        sign_in(proxy, open_browser=fake_browser(error="access_denied"), timeout=10)


def test_sign_in_rejects_a_forged_callback(proxy):
    with pytest.raises(LoginError, match="state"):
        sign_in(proxy, open_browser=fake_browser(wrong_state=True), timeout=10)


def test_sign_in_times_out_when_nobody_logs_in(proxy):
    with pytest.raises(LoginError, match="นานเกินไป"):
        sign_in(proxy, open_browser=lambda url: True, timeout=1)


def test_sign_in_fails_cleanly_when_server_is_down():
    with pytest.raises(LoginError, match="ติดต่อ server"):
        sign_in("http://127.0.0.1:9", open_browser=lambda url: True, timeout=1)


# ---------- App: client and services ----------

def test_client_needs_a_login_first(proxy):
    client = ZipZapCloudClient(proxy)

    assert not client.is_configured
    with pytest.raises(AINotConfiguredError, match="login ด้วย Google"):
        client.generate("hi")
    assert client.usage() is None


def test_client_generates_and_shows_the_quota_message(proxy):
    client = ZipZapCloudClient(proxy, session_for(proxy))

    assert client.generate("1") == "สวัสดี"
    assert client.usage()["used"] == 1
    client.generate("2")
    with pytest.raises(AIServiceError, match="ครบ 2 ครั้ง"):
        client.generate("3")


def test_client_usage_reports_an_expired_login(proxy):
    assert ZipZapCloudClient(proxy, "zs-" + "0" * 64).usage() == {"expired": True}


def test_client_cannot_upload_files(proxy):
    client = ZipZapCloudClient(proxy, session_for(proxy))

    assert not client.supports_file_upload
    with pytest.raises(AIServiceError):
        client.upload_file("doc.pdf")


def test_services_sign_in_and_out_persist(proxy, tmp_path, monkeypatch):
    monkeypatch.setenv("ZIPZAP_PROXY_URL", proxy)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(core.config, "is_frozen", lambda: True)
    paths = [str(tmp_path / name) for name in ("config.json", "log.txt", "log.json")]

    services = build_services(*paths)
    assert not services.llm.is_configured
    services.sign_in_with_google(open_browser=fake_browser())
    session = services.zipzap.session

    reopened = build_services(*paths)  # A restart keeps the login
    assert reopened.llm.is_configured
    assert reopened.config.get("zipzap_email") == "a@example.com"

    reopened.sign_out()
    assert not reopened.llm.is_configured
    assert build_services(*paths).config.get("zipzap_session") == ""
    assert call(proxy, token=session)[0] == 401  # Logged out on the server too
