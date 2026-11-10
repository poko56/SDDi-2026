import json
import os
import re
import uuid

from core.paths import is_frozen, resource_path

API_KEY_ENV_VAR = "GEMINI_API_KEY"
PROXY_URL_ENV_VAR = "ZIPZAP_PROXY_URL"
DEFAULT_PROXY_URL = "https://185-84-160-168.sslip.io"
_INSTALL_ID_RE = re.compile(r"zz-[0-9a-f]{32}")


class ConfigManager:
    """Loads and saves user settings (theme, API key, excluded folders) as JSON."""

    DEFAULTS = {
        "theme": "Light",
        "ai_provider": "zipzap",
        "install_id": "",
        "gemini_api_key": "",
        "ollama_url": "http://localhost:11434",
        "ollama_model": "",
        "excluded_folders": [],
    }

    def __init__(self, path):
        self.path = path
        self._data = dict(self.DEFAULTS)
        self._data.update(self._load())

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            # A corrupt config must not stop the app from starting
            return {}

    def get(self, key):
        return self._data.get(key, self.DEFAULTS.get(key))

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp_path = self.path + ".tmp"
        # The file holds the API key: create it readable by the owner only
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=4)
        os.replace(tmp_path, self.path)

    def install_id(self):
        """Random id this install sends to the ZipZap AI server, which counts daily uses per id."""
        value = self.get("install_id") or ""
        if not _INSTALL_ID_RE.fullmatch(value):
            value = "zz-" + uuid.uuid4().hex
            self.set("install_id", value)
        return value

    @staticmethod
    def proxy_url():
        return os.environ.get(PROXY_URL_ENV_VAR, "").strip() or DEFAULT_PROXY_URL

    def resolve_api_key(self):
        """Key typed in Settings, else the GEMINI_API_KEY env var, else a developer's local api_key.txt.

        Release builds never bundle a key: each user supplies their own.
        """
        key = (self.get("gemini_api_key") or "").strip()
        if key:
            return key
        key = os.environ.get(API_KEY_ENV_VAR, "").strip()
        if key:
            return key
        if not is_frozen():
            try:
                with open(resource_path("api_key.txt"), "r", encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                pass
        return ""
