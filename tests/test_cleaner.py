import os
import time

from conftest import write
from core.cleaner import QUICK_HASH_SIZE, ScanOptions, StorageCleaner

ONLY_DUPLICATES = ScanOptions(duplicates=True, junk=False, large=False)
ONLY_JUNK = ScanOptions(duplicates=False, junk=True, large=False)


def names(results):
    return {os.path.basename(r.path) for r in results}


def test_duplicates_keep_shallowest_copy_as_original(logger, workdir):
    write(workdir / "a.txt", "same")
    write(workdir / "sub" / "b.txt", "same")
    write(workdir / "c.txt", "different")

    results = StorageCleaner(logger).scan(str(workdir), ONLY_DUPLICATES)

    assert len(results) == 1
    assert results[0].path == str(workdir / "sub" / "b.txt")
    assert results[0].original == str(workdir / "a.txt")
    assert results[0].type == "duplicate"


def test_duplicates_three_copies_report_two(logger, workdir):
    for name in ("a.txt", "b.txt", "c.txt"):
        write(workdir / name, "same")

    results = StorageCleaner(logger).scan(str(workdir), ONLY_DUPLICATES)

    assert names(results) == {"b.txt", "c.txt"}


def test_same_size_different_content_is_not_duplicate(logger, workdir):
    write(workdir / "a.txt", "aaaa")
    write(workdir / "b.txt", "bbbb")

    assert StorageCleaner(logger).scan(str(workdir), ONLY_DUPLICATES) == []


def test_large_files_differing_after_quick_hash_are_not_duplicates(logger, workdir):
    head = "x" * QUICK_HASH_SIZE
    write(workdir / "a.bin", head + "tail-A")
    write(workdir / "b.bin", head + "tail-B")
    write(workdir / "c.bin", head + "tail-A")

    results = StorageCleaner(logger).scan(str(workdir), ONLY_DUPLICATES)

    assert names(results) == {"c.bin"}


def test_empty_files_are_not_duplicates(logger, workdir):
    (workdir / "a.txt").write_text("")
    (workdir / "b.txt").write_text("")

    assert StorageCleaner(logger).scan(str(workdir), ONLY_DUPLICATES) == []


def test_junk_matches_extensions_case_insensitive(logger, workdir):
    write(workdir / "x.tmp")
    write(workdir / "y.LOG")
    write(workdir / "keep.txt")

    assert names(StorageCleaner(logger).scan(str(workdir), ONLY_JUNK)) == {"x.tmp", "y.LOG"}


def test_large_files_require_size_and_age(logger, workdir):
    big_old = write(workdir / "big_old.bin", "x" * 2048)
    write(workdir / "big_new.bin", "x" * 2048)
    small_old = write(workdir / "small_old.bin", "x")
    old = time.time() - 40 * 24 * 3600
    os.utime(big_old, (old, old))
    os.utime(small_old, (old, old))

    options = ScanOptions(duplicates=False, junk=False, large=True, large_min_mb=1 / 1024, large_min_days=30)
    results = StorageCleaner(logger).scan(str(workdir), options)

    assert [r.path for r in results] == [str(big_old)]


def test_one_walk_reports_every_enabled_check(logger, workdir):
    write(workdir / "a.txt", "same")
    write(workdir / "b.txt", "same")
    write(workdir / "x.tmp")

    results = StorageCleaner(logger).scan(str(workdir), ScanOptions())

    assert {(os.path.basename(r.path), r.type) for r in results} == {("b.txt", "duplicate"), ("x.tmp", "junk")}
