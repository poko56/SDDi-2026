"""AI providers behind one small interface, so the rest of the app never imports an SDK.

AIAssistant and FileOrganizer only call:
    is_configured, generate(contents, vision=False), supports_file_upload,
    upload_file(path), delete_file(handle), max_prompt_files
ZipZapCloudClient (Gemini through the team's server, no key needed), GeminiClient (the
user's own key) and OllamaClient (local, core/ollama.py) all provide them, and AIRouter
forwards to whichever one the user picked in Settings.
"""
import json
import urllib.error
import urllib.request

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

CHAT_MODEL = "gemini-flash-lite-latest"
VISION_MODEL = "gemini-3.6-flash"


class AIServiceError(Exception):
    pass


class AINotConfiguredError(AIServiceError):
    pass


class GeminiClient:
    name = "gemini"
    label = "Gemini (Cloud)"
    keeps_data_local = False
    supports_file_upload = True
    max_prompt_files = 500

    def __init__(self, api_key=""):
        self._api_key = ""
        self._client = None
        self.set_api_key(api_key)

    @property
    def is_configured(self):
        return bool(self._api_key)

    @property
    def model_description(self):
        return f"{CHAT_MODEL} / {VISION_MODEL}"

    def set_api_key(self, api_key):
        self._api_key = (api_key or "").strip()
        self._client = None  # Created lazily and reused across calls

    def _get_client(self):
        if not self._api_key:
            raise AINotConfiguredError("ยังไม่ได้ใส่ Gemini API Key ในหน้า Settings")
        if self._client is None:
            self._client = self._new_client()
        return self._client

    def _new_client(self):
        return genai.Client(api_key=self._api_key)

    def generate(self, contents, vision=False):
        """Send a prompt (text, PIL images or uploaded files) and return the reply text."""
        model = VISION_MODEL if vision else CHAT_MODEL
        try:
            response = self._get_client().models.generate_content(model=model, contents=contents)
        except AINotConfiguredError:
            raise
        except Exception as e:  # The SDK raises many unrelated types for network/API errors
            raise AIServiceError(str(e)) from e
        return response.text or ""

    def upload_file(self, path):
        try:
            return self._get_client().files.upload(file=path)
        except AINotConfiguredError:
            raise
        except Exception as e:
            raise AIServiceError(str(e)) from e

    def delete_file(self, uploaded):
        try:
            self._get_client().files.delete(name=uploaded.name)
        except Exception:
            # Best effort: Gemini deletes uploaded files on its own after 48h
            pass


class ZipZapCloudClient(GeminiClient):
    """Gemini through the team's proxy server (server/zipzap_proxy.py).

    The real API key stays on the server; this client sends a random install id
    instead, and the server limits how many requests each install may make per day.
    """

    name = "zipzap"
    label = "ZipZap AI"
    supports_file_upload = False  # The proxy only forwards generateContent; PDFs are sent as text or page images
    USAGE_TIMEOUT = 5

    def __init__(self, base_url, install_id):
        self.base_url = (base_url or "").strip().rstrip("/")
        super().__init__(install_id)

    @property
    def is_configured(self):
        return bool(self.base_url and self._api_key)

    @property
    def model_description(self):
        return "Gemini ผ่าน server ของทีม ZipZap (ไม่ต้องใช้ API key)"

    def _new_client(self):
        return genai.Client(api_key=self._api_key, http_options=genai_types.HttpOptions(base_url=self.base_url))

    def generate(self, contents, vision=False):
        try:
            return super().generate(contents, vision)
        except AIServiceError as e:
            cause = e.__cause__
            if isinstance(cause, genai_errors.APIError) and cause.code in (401, 413, 429, 502, 503) and cause.message:
                raise AIServiceError(cause.message) from cause  # The proxy's own Thai message
            raise

    def upload_file(self, path):
        raise AIServiceError("ZipZap AI รับไฟล์โดยตรงไม่ได้")

    def delete_file(self, uploaded):
        pass

    def usage(self):
        """Today's {"used", "limit", "remaining"} for this install, or None if the server cannot be reached."""
        request = urllib.request.Request(f"{self.base_url}/v1/usage", headers={"x-goog-api-key": self._api_key})
        try:
            with urllib.request.urlopen(request, timeout=self.USAGE_TIMEOUT) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, OSError, ValueError):
            return None


class AIRouter:
    """Proxy that forwards every call to the active provider.

    Services keep a reference to this one object, so switching provider in
    Settings takes effect everywhere without rebuilding anything.
    """

    def __init__(self, providers, active):
        self.providers = {p.name: p for p in providers}
        self._active = None
        self.use(active)

    def use(self, name):
        if name not in self.providers:
            name = next(iter(self.providers))
        self._active = self.providers[name]

    @property
    def active(self):
        return self._active

    @property
    def active_name(self):
        return self._active.name

    def __getattr__(self, attr):
        # Only reached for attributes not defined on the router itself
        return getattr(self._active, attr)
