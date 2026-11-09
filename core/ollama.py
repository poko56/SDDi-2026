"""Local AI through Ollama (https://ollama.com), talking to its HTTP API with the standard library only.

Files never leave the computer when the server is on localhost. The same
client also works with an Ollama server elsewhere (e.g. a VPS); the UI then
warns that data does leave the machine.
"""
import base64
import io
import json
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

from core.llm import AINotConfiguredError, AIServiceError

DEFAULT_URL = "http://localhost:11434"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
CONTEXT_TOKENS = 8192  # Ollama's default window is too small for the AI Chat file list
MAX_IMAGE_SIDE = 1024  # Downscale photos: vision models gain little beyond this and get much slower
STATUS_TIMEOUT = 3
GENERATE_TIMEOUT = 300  # The first request also loads the model into memory


class LocalModel:
    def __init__(self, name, size_gb, min_ram_gb, note):
        self.name = name
        self.size_gb = size_gb
        self.min_ram_gb = min_ram_gb
        self.note = note


# Vision-capable models (Smart Rename reads images) that also handle Thai reasonably, largest first
RECOMMENDED_MODELS = [
    LocalModel("gemma3:12b", 8.1, 16, "แม่นกว่า อ่านภาษาไทยได้ดีกว่า แต่ช้ากว่า"),
    LocalModel("gemma3:4b", 3.3, 8, "เร็ว เหมาะกับเครื่องทั่วไป"),
]


def recommend_model(ram_gb):
    """Pick the largest recommended model that fits in RAM, or None if the machine is too small."""
    if ram_gb is None:
        return RECOMMENDED_MODELS[-1]
    for model in RECOMMENDED_MODELS:
        if ram_gb >= model.min_ram_gb:
            return model
    return None


def validate_url(url):
    """Accept only http(s) URLs: urllib would otherwise also open file:// and other schemes."""
    url = (url or "").strip().rstrip("/") or DEFAULT_URL
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("URL ต้องขึ้นต้นด้วย http:// หรือ https:// เช่น http://localhost:11434")
    return url


class OllamaClient:
    name = "ollama"
    label = "Local AI (Ollama)"
    supports_file_upload = False
    max_prompt_files = 150  # Long prompts are slow on a laptop; keep AI Chat responsive

    def __init__(self, base_url=DEFAULT_URL, model=""):
        self.base_url = validate_url(base_url)
        self.model = (model or "").strip()

    # ---------- Provider interface ----------

    @property
    def is_configured(self):
        return bool(self.model)

    @property
    def keeps_data_local(self):
        return urllib.parse.urlparse(self.base_url).hostname in LOCAL_HOSTS

    @property
    def model_description(self):
        return self.model or "ยังไม่ได้เลือกโมเดล"

    def configure(self, base_url, model):
        self.base_url = validate_url(base_url)
        self.model = (model or "").strip()

    def generate(self, contents, vision=False):
        """Send text and PIL images to the chosen model and return its reply."""
        if not self.model:
            raise AINotConfiguredError("ยังไม่ได้เลือกโมเดล Local AI ในหน้า Settings")
        parts = contents if isinstance(contents, list) else [contents]
        texts = [p for p in parts if isinstance(p, str)]
        images = [self._encode_image(p) for p in parts if isinstance(p, Image.Image)]
        message = {"role": "user", "content": "\n\n".join(texts)}
        if images:
            message["images"] = images
        payload = {
            "model": self.model,
            "messages": [message],
            "stream": False,
            "options": {"num_ctx": CONTEXT_TOKENS, "temperature": 0.2},
        }
        reply = self._request("/api/chat", payload, timeout=GENERATE_TIMEOUT)
        return reply.get("message", {}).get("content", "")

    def upload_file(self, path):
        raise AIServiceError("Local AI รับไฟล์โดยตรงไม่ได้")

    def delete_file(self, handle):
        pass

    # ---------- HTTP helpers ----------

    @staticmethod
    def _encode_image(img):
        img = img.convert("RGB")
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = io.BytesIO()
        img.save(buffer, "JPEG", quality=90)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    def _build_request(self, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        return urllib.request.Request(self.base_url + path, data=data, headers=headers,
                                      method="POST" if data else "GET")

    def _request(self, path, payload=None, timeout=STATUS_TIMEOUT):
        try:
            with urllib.request.urlopen(self._build_request(path, payload), timeout=timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = self._error_detail(e)
            if e.code == 404 and "not found" in detail:
                raise AIServiceError(f"ยังไม่ได้ดาวน์โหลดโมเดล {self.model} (กดดาวน์โหลดในหน้า Settings)") from e
            raise AIServiceError(f"Ollama ตอบกลับผิดพลาด ({e.code}): {detail}") from e
        except (urllib.error.URLError, OSError) as e:
            raise AIServiceError(f"เชื่อมต่อ Ollama ที่ {self.base_url} ไม่ได้ (เปิดโปรแกรม Ollama หรือยัง?)") from e
        except json.JSONDecodeError as e:
            raise AIServiceError("Ollama ตอบกลับในรูปแบบที่อ่านไม่ได้") from e

    @staticmethod
    def _error_detail(error):
        try:
            return json.loads(error.read()).get("error", "")
        except (ValueError, OSError):
            return str(error)
