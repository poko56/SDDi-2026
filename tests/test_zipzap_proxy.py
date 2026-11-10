import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from core.config import ConfigManager
from core.llm import AIServiceError, ZipZapCloudClient
from server.zipzap_proxy import Settings, UsageStore, make_server

REAL_KEY = "real-secret-key"
TOKEN = "zz-" + "a" * 32
OTHER_TOKEN = "zz-" + "b" * 32
GEN_PATH = "/v1beta/models/gemini-flash-lite-latest:generateContent"


class FakeGemini(BaseHTTPRequestHandler):
    requests = []
    reject_key = False

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        FakeGemini.requests.append({"path": self.path, "key": self.headers.get("x-goog-api-key"),
                                    "body": json.loads(body)})
        if FakeGemini.reject_key:
            code, reply = 400, json.dumps({"error": {"code": 400, "message": "API key not valid.",
                                                     "status": "INVALID_ARGUMENT",
                                                     "details": [{"reason": "API_KEY_INVALID"}]}})
        else:
            code = 200
            reply = json.dumps({"candidates": [{"content": {"role": "model", "parts": [{"text": "สวัสดี"}]}}]})
        data = reply.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def proxy(tmp_path):
    FakeGemini.requests = []
    FakeGemini.reject_key = False
    upstream = start(ThreadingHTTPServer(("127.0.0.1", 0), FakeGemini))
    settings = Settings(api_key=REAL_KEY, upstream=f"http://127.0.0.1:{upstream.server_port}",
                        port=0, per_install=2, per_ip=3, total=4, trust_forwarded_for=False)
    server = start(make_server(settings, UsageStore(str(tmp_path / "usage.db"))))
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    upstream.shutdown()


def call(url, path=GEN_PATH, token=TOKEN, body=b'{"contents": []}', method="POST"):
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


def test_forwards_with_real_key_and_hides_install_token(proxy):
    code, reply = call(proxy)

    assert code == 200
    assert reply["candidates"][0]["content"]["parts"][0]["text"] == "สวัสดี"
    assert FakeGemini.requests[0]["key"] == REAL_KEY
    assert FakeGemini.requests[0]["path"] == GEN_PATH


@pytest.mark.parametrize("token", [None, "AIzaFakeKey", "zz-short"])
def test_rejects_missing_or_bad_install_token(proxy, token):
    code, reply = call(proxy, token=token)

    assert code == 401
    assert FakeGemini.requests == []


@pytest.mark.parametrize("path", ["/v1beta/models/gemini-ultra:generateContent",
                                  "/v1beta/files", "/upload/v1beta/files"])
def test_only_forwards_allowed_models_and_endpoints(proxy, path):
    code, _ = call(proxy, path=path)

    assert code == 404
    assert FakeGemini.requests == []


def test_limits_each_install_per_day(proxy):
    assert call(proxy)[0] == 200
    assert call(proxy)[0] == 200
    code, reply = call(proxy)

    assert code == 429
    assert "ครบ 2 ครั้ง" in reply["error"]["message"]
    assert len(FakeGemini.requests) == 2


def test_limits_each_ip_and_the_whole_day(proxy):
    tokens = ["zz-" + c * 32 for c in "abcdef"]
    codes = [call(proxy, token=t)[0] for t in tokens[:4]]

    assert codes == [200, 200, 200, 429]  # per_ip=3 from the same address


def test_usage_reports_remaining_requests(proxy):
    call(proxy)
    code, usage = call(proxy, path="/v1/usage", method="GET")

    assert code == 200
    assert usage == {"used": 1, "limit": 2, "remaining": 1}


def test_rejects_empty_body(proxy):
    assert call(proxy, body=b"")[0] == 413


def test_client_generates_through_proxy(proxy):
    client = ZipZapCloudClient(proxy, TOKEN)

    assert client.is_configured
    assert client.generate("hello") == "สวัสดี"
    assert FakeGemini.requests[0]["key"] == REAL_KEY
    assert FakeGemini.requests[0]["path"].endswith("/models/gemini-flash-lite-latest:generateContent")
    assert client.usage()["used"] == 1


def test_client_shows_the_proxy_quota_message(proxy):
    client = ZipZapCloudClient(proxy, TOKEN)
    client.generate("1")
    client.generate("2")

    with pytest.raises(AIServiceError, match="ครบ 2 ครั้ง"):
        client.generate("3")


def test_bad_server_key_is_reported_as_a_server_problem(proxy):
    FakeGemini.reject_key = True

    with pytest.raises(AIServiceError, match="server ของ ZipZap ตั้งค่า Gemini key ไม่ถูกต้อง"):
        ZipZapCloudClient(proxy, TOKEN).generate("hi")


def test_client_cannot_upload_files(proxy):
    client = ZipZapCloudClient(proxy, TOKEN)

    assert not client.supports_file_upload
    with pytest.raises(AIServiceError):
        client.upload_file("doc.pdf")


def test_client_usage_is_none_when_server_is_down():
    assert ZipZapCloudClient("http://127.0.0.1:9", TOKEN).usage() is None


def test_install_id_is_created_once_and_kept(tmp_path):
    path = str(tmp_path / "config.json")
    first = ConfigManager(path).install_id()

    assert first.startswith("zz-") and len(first) == 35
    assert ConfigManager(path).install_id() == first


def test_bad_install_id_is_replaced(tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    config.set("install_id", "not-valid")

    assert config.install_id().startswith("zz-")
