"""Local AI tests against a fake Ollama HTTP server (no real Ollama or model needed)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

from core.llm import AINotConfiguredError, AIServiceError
from core.ollama import OllamaClient


class FakeOllama(BaseHTTPRequestHandler):
    requests = []
    installed = ["gemma3:4b"]

    def log_message(self, *args):
        pass

    def _send(self, code, body):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/version":
            self._send(200, {"version": "0.9.0"})
        elif self.path == "/api/tags":
            self._send(200, {"models": [{"name": m} for m in self.installed]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.requests.append((self.path, body))
        if self.path == "/api/chat":
            if body["model"] not in self.installed:
                self._send(404, {"error": f"model '{body['model']}' not found"})
            else:
                self._send(200, {"message": {"role": "assistant", "content": "Receipt_Starbucks"}})
        elif self.path == "/api/pull":
            lines = [{"status": "pulling manifest"},
                     {"status": "downloading", "total": 100, "completed": 40},
                     {"status": "downloading", "total": 100, "completed": 100},
                     {"status": "success"}]
            if body["model"] == "broken:model":
                lines = [{"error": "pull model manifest: file does not exist"}]
            self._send(200, b"\n".join(json.dumps(line).encode() for line in lines))


@pytest.fixture
def server():
    FakeOllama.requests = []
    httpd = HTTPServer(("127.0.0.1", 0), FakeOllama)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


# ---------- OllamaClient ----------

def test_status_and_installed_models(server):
    client = OllamaClient(server)
    assert client.server_version() == "0.9.0"
    assert client.installed_models() == ["gemma3:4b"]


def test_server_missing_reports_none():
    assert OllamaClient("http://127.0.0.1:9").server_version() is None


def test_generate_sends_text_and_downscaled_image(server):
    client = OllamaClient(server, "gemma3:4b")

    reply = client.generate(["Name this file", Image.new("RGB", (3000, 2000), "red")], vision=True)

    assert reply == "Receipt_Starbucks"
    path, body = FakeOllama.requests[-1]
    assert path == "/api/chat"
    message = body["messages"][0]
    assert message["content"] == "Name this file"
    assert len(message["images"]) == 1
    assert body["stream"] is False
    assert body["options"]["num_ctx"] >= 8192


def test_generate_without_model_is_not_configured(server):
    client = OllamaClient(server)
    assert not client.is_configured
    with pytest.raises(AINotConfiguredError):
        client.generate("hi")


def test_generate_with_missing_model_explains_download(server):
    with pytest.raises(AIServiceError, match="ยังไม่ได้ดาวน์โหลดโมเดล"):
        OllamaClient(server, "llama9:70b").generate("hi")


def test_generate_when_server_is_down():
    with pytest.raises(AIServiceError, match="เชื่อมต่อ Ollama"):
        OllamaClient("http://127.0.0.1:9", "gemma3:4b").generate("hi")


def test_pull_reports_progress(server):
    events = []
    OllamaClient(server).pull_model("gemma3:12b", lambda *e: events.append(e))
    assert events[0] == ("pulling manifest", 0, 0)
    assert ("downloading", 100, 100) in events
    assert FakeOllama.requests[-1] == ("/api/pull", {"model": "gemma3:12b", "stream": True})


def test_pull_error_is_raised(server):
    with pytest.raises(AIServiceError, match="does not exist"):
        OllamaClient(server).pull_model("broken:model")
