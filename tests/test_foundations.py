import os
import sys

import pytest

from conftest import write
from core.file_types import category_of, format_size, is_junk
from core.paths import safe_join, unique_path


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


# ---------- unique_path ----------

def test_unique_path(workdir):
    target = workdir / "a.txt"
    assert unique_path(str(target)) == str(target)
    write(target)
    write(workdir / "a_1.txt")
    assert unique_path(str(target)) == str(workdir / "a_2.txt")


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
