import json
import os


class ConfigManager:
    """Loads and saves user settings (theme, API key, excluded folders) as JSON."""

    DEFAULTS = {
        "theme": "Light",
        "ai_provider": "gemini",
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
