"""Tests for the small shared building blocks: paths, exclusions, file types, config, stats."""
import json
import os
import stat
import sys

import pytest

from conftest import write
from core.config import ConfigManager
from core.exclusion import ExclusionPolicy
from core.file_types import category_of, format_size, is_junk
from core.paths import TRASH_DIR_NAME, safe_join, unique_path
from core.stats import StorageAnalyzer


# ---------- safe_join ----------

def test_safe_join_inside_root(workdir):
    assert safe_join(str(workdir), "sub/a.txt") == os.path.realpath(workdir / "sub" / "a.txt")


@pytest.mark.parametrize("rel_path", ["../outside.txt", "sub/../../outside.txt", "/etc/passwd", ""])
def test_safe_join_rejects_escapes(workdir, rel_path):
    assert safe_join(str(workdir), rel_path) is None


@pytest.mark.skipif(sys.platform.startswith("win"), reason="symlinks need admin rights on Windows")
def test_safe_join_rejects_symlink_escape(workdir, tmp_path):
    outside = tmp_path / "secret"
    outside.mkdir()
    os.symlink(outside, workdir / "link")
    assert safe_join(str(workdir), "link/file.txt") is None


def test_safe_join_without_root():
    assert safe_join("", "a.txt") is None


# ---------- StorageAnalyzer ----------

def test_storage_stats_by_category(workdir):
    write(workdir / "a.pdf", "x" * 10)
    write(workdir / "sub" / "b.jpg", "x" * 20)
    write(workdir / "sub" / "deeper" / "c.mp3", "x" * 5)
    write(workdir / "d.zip", "x" * 7)
    write(workdir / TRASH_DIR_NAME / "e.pdf", "x" * 100)

    stats = StorageAnalyzer().analyze(str(workdir))

    assert stats.file_count == 4
    assert (stats.documents_bytes, stats.media_bytes, stats.other_bytes) == (10, 25, 7)
    assert stats.total_bytes == 42
    assert stats.disk_free_bytes > 0


def test_storage_stats_missing_folder(workdir):
    assert StorageAnalyzer().analyze(str(workdir / "nope")).file_count == 0


# ---------- unique_path ----------

def test_unique_path(workdir):
    target = workdir / "a.txt"
    assert unique_path(str(target)) == str(target)
    write(target)
    write(workdir / "a_1.txt")
    assert unique_path(str(target)) == str(workdir / "a_2.txt")


# ---------- ExclusionPolicy ----------

def test_exclusion_matches_folder_and_children(workdir):
    policy = ExclusionPolicy([str(workdir / "private")])
    assert policy.is_excluded(str(workdir / "private"))
    assert policy.is_excluded(str(workdir / "private" / "deep" / "a.txt"))
    assert not policy.is_excluded(str(workdir / "private_other" / "a.txt"))
    assert not policy.is_excluded(str(workdir / "a.txt"))


def test_exclusion_update_applies_to_all_holders(workdir):
    policy = ExclusionPolicy()
    assert not policy.is_excluded(str(workdir / "a.txt"))
    policy.update([str(workdir)])
    assert policy.is_excluded(str(workdir / "a.txt"))
    assert policy.folders == [os.path.abspath(workdir)]


# ---------- file types ----------

@pytest.mark.parametrize("name, category", [
    ("a.JPG", "Images"), ("b.heic", "Images"), ("c.pdf", "Documents"), ("d.mkv", "Videos"),
    ("e.flac", "Audio"), ("f.7z", "Archives"), ("g.xyz", "Others"), ("noext", "Others"),
])
def test_category_of(name, category):
    assert category_of(name) == category


def test_is_junk():
    assert is_junk("x.TMP")
    assert not is_junk("x.txt")


@pytest.mark.parametrize("size, text", [
    (0, "0 B"), (15, "15 B"), (2048, "2.0 KB"), (5 * 1024 ** 2, "5.0 MB"), (3 * 1024 ** 3, "3.00 GB"),
])
def test_format_size(size, text):
    assert format_size(size) == text


# ---------- ConfigManager ----------

def test_config_defaults_when_missing(tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    assert config.get("theme") == "Light"
    assert config.get("excluded_folders") == []


def test_config_survives_corrupt_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{broken")
    assert ConfigManager(str(path)).get("theme") == "Light"


def test_config_set_persists(tmp_path):
    path = tmp_path / "sub" / "config.json"
    ConfigManager(str(path)).set("theme", "Dark")

    assert ConfigManager(str(path)).get("theme") == "Dark"
    assert json.loads(path.read_text())["theme"] == "Dark"


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX permissions")
def test_config_file_is_private(tmp_path):
    path = tmp_path / "config.json"
    ConfigManager(str(path)).set("gemini_api_key", "secret")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_api_key_prefers_saved_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    config = ConfigManager(str(tmp_path / "config.json"))
    config.set("gemini_api_key", "  saved  ")
    assert config.resolve_api_key() == "saved"


def test_api_key_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert ConfigManager(str(tmp_path / "config.json")).resolve_api_key() == "from-env"
