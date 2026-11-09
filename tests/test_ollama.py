"""Local AI tests against a fake Ollama HTTP server (no real Ollama or model needed)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from PIL import Image

import core.config
from conftest import FakeLLM, write
from core.llm import AINotConfiguredError, AIRouter, AIServiceError, GeminiClient
from core.ollama import OllamaClient, RECOMMENDED_MODELS, recommend_model, validate_url
from core.organizer import FileOrganizer, extract_pdf_text
from core.services import build_services


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


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://host", "localhost:11434", "http://"])
def test_validate_url_rejects_non_http(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_validate_url_defaults_and_trims():
    assert validate_url("") == "http://localhost:11434"
    assert validate_url(" http://10.0.0.5:11434/ ") == "http://10.0.0.5:11434"


def test_keeps_data_local_only_for_loopback():
    assert OllamaClient("http://localhost:11434").keeps_data_local
    assert OllamaClient("http://127.0.0.1:11434").keeps_data_local
    assert not OllamaClient("https://my-vps.example.com").keeps_data_local


@pytest.mark.parametrize("ram, expected", [
    (32, "gemma3:12b"), (16, "gemma3:12b"), (8, "gemma3:4b"), (4, None), (None, RECOMMENDED_MODELS[-1].name),
])
def test_recommend_model(ram, expected):
    model = recommend_model(ram)
    assert (model.name if model else None) == expected


# ---------- AIRouter and services ----------

def test_router_forwards_to_active_provider():
    gemini, local = GeminiClient(""), OllamaClient("http://localhost:11434", "gemma3:4b")
    router = AIRouter([gemini, local], "gemini")
    assert not router.is_configured
    assert router.supports_file_upload

    router.use("ollama")
    assert router.is_configured
    assert router.active is local
    assert router.max_prompt_files == local.max_prompt_files


def test_router_unknown_provider_falls_back_to_first():
    router = AIRouter([GeminiClient(""), OllamaClient()], "something-else")
    assert router.active_name == "gemini"


def test_services_switch_provider_and_persist(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(core.config, "is_frozen", lambda: True)
    paths = [str(tmp_path / n) for n in ("config.json", "log.txt", "log.json")]
    services = build_services(*paths)

    services.set_local_ai("http://127.0.0.1:11434", "gemma3:4b")
    services.set_ai_provider("ollama")

    assert services.organizer.llm.active_name == "ollama"
    reloaded = build_services(*paths)
    assert reloaded.llm.active_name == "ollama"
    assert reloaded.ollama.model == "gemma3:4b"
    with pytest.raises(ValueError):
        services.set_local_ai("file:///etc", "x")


# ---------- PDF fallback for providers that cannot read PDF files ----------

def text_pdf(path, text):
    """A minimal one-page PDF with a real text layer."""
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>stream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))
    return path


def test_extract_pdf_text(workdir):
    assert "Invoice 42" in extract_pdf_text(str(text_pdf(workdir / "a.pdf", "Invoice 42")))


def test_local_ai_renames_pdf_from_its_text(logger, workdir):
    pdf = text_pdf(workdir / "scan.pdf", "Invoice 42 Web Hosting")
    llm = FakeLLM(reply="Invoice_42", supports_file_upload=False)

    ok, new_name = FileOrganizer(logger, llm).smart_rename(str(pdf))

    assert (ok, new_name) == (True, "Invoice_42.pdf")
    assert llm.uploaded == []
    assert "Invoice 42 Web Hosting" in llm.calls[0][0][1]


def test_local_ai_reads_scanned_pdf_as_image(logger, workdir):
    scanned = workdir / "scan.pdf"
    Image.new("RGB", (200, 300), "white").save(scanned, "PDF")
    llm = FakeLLM(reply="Scanned_Invoice", supports_file_upload=False)

    ok, new_name = FileOrganizer(logger, llm).smart_rename(str(scanned))

    assert (ok, new_name) == (True, "Scanned_Invoice.pdf")
    contents, vision = llm.calls[0]
    assert isinstance(contents[1], Image.Image)
    assert contents[1].size == (200, 300)


def test_local_ai_rejects_pdf_with_no_text_or_image(logger, workdir):
    blank = text_pdf(workdir / "blank.pdf", "")
    llm = FakeLLM(supports_file_upload=False)

    ok, msg = FileOrganizer(logger, llm).smart_rename(str(blank))

    assert not ok
    assert "ไม่มีทั้งข้อความและรูปภาพ" in msg
    assert llm.calls == []


def test_local_ai_reports_unreadable_pdf(logger, workdir):
    broken = write(workdir / "broken.pdf", "not a pdf")
    ok, msg = FileOrganizer(logger, FakeLLM(supports_file_upload=False)).smart_rename(str(broken))
    assert not ok
    assert broken.exists()


def test_assistant_sends_fewer_files_to_local_ai(workdir):
    from core.ai_assistant import AIAssistant
    for i in range(20):
        write(workdir / f"f{i}.txt")
    llm = FakeLLM(max_prompt_files=5)

    AIAssistant(llm).ask_ai(str(workdir), "hi")

    assert llm.calls[0][0].count("- f") == 5
