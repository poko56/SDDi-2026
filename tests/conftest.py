import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
