import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm import AIServiceError  # noqa: E402
from core.logger import ActionLogger  # noqa: E402


@pytest.fixture
def logger(tmp_path):
    """ActionLogger that writes into a temp dir instead of ~/.zipzap."""
    return ActionLogger(str(tmp_path / "action_log.txt"), str(tmp_path / "action_log.json"))


@pytest.fixture
def workdir(tmp_path):
    """Empty folder to scan/sort, separate from the logger's files."""
    folder = tmp_path / "work"
    folder.mkdir()
    return folder


def write(path, content="data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class FakeLLM:
    """Stands in for an AI provider so tests never call a real one."""

    label = "Fake AI"
    keeps_data_local = True
    not_configured_message = "ยังไม่ได้ใส่ Gemini API Key ในหน้า Settings"

    def __init__(self, reply="fake_reply", configured=True, error=None, supports_file_upload=True,
                 max_prompt_files=500):
        self.reply = reply
        self.is_configured = configured
        self.error = error
        self.supports_file_upload = supports_file_upload
        self.max_prompt_files = max_prompt_files
        self.calls = []
        self.uploaded = []
        self.deleted = []

    def generate(self, contents, vision=False):
        self.calls.append((contents, vision))
        if self.error:
            raise AIServiceError(self.error)
        return self.reply

    def upload_file(self, path):
        handle = f"uploaded:{path}"
        self.uploaded.append(handle)
        return handle

    def delete_file(self, handle):
        self.deleted.append(handle)


@pytest.fixture
def fake_llm():
    return FakeLLM()
