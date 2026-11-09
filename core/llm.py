"""AI providers behind one small interface, so the rest of the app never imports an SDK.

AIAssistant and FileOrganizer only call:
    is_configured, generate(contents, vision=False), supports_file_upload,
    upload_file(path), delete_file(handle), max_prompt_files
GeminiClient (cloud) and OllamaClient (local, core/ollama.py) both provide them,
and AIRouter forwards to whichever one the user picked in Settings.
"""
from google import genai

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
            self._client = genai.Client(api_key=self._api_key)
        return self._client

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
