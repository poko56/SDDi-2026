import os
import sys

import pytest

from conftest import write
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
