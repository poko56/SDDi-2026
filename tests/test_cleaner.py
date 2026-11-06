import os

from conftest import write
from core.cleaner import QUICK_HASH_SIZE, ScanOptions, StorageCleaner

ONLY_DUPLICATES = ScanOptions(duplicates=True, junk=False, large=False)


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
