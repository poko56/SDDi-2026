import datetime
import os

from conftest import write
from core.exclusion import ExclusionPolicy
from core.organizer import ByFileType, ByModifiedMonth, FileOrganizer


def test_organize_by_type_moves_into_category_folders(logger, workdir):
    write(workdir / "photo.JPG")
    write(workdir / "doc.pdf")
    write(workdir / "song.mp3")
    write(workdir / "weird.xyz")

    ok, message = FileOrganizer(logger).organize_folder(str(workdir), ByFileType())

    assert ok
    assert "4" in message
    assert (workdir / "Images" / "photo.JPG").exists()
    assert (workdir / "Documents" / "doc.pdf").exists()
    assert (workdir / "Audio" / "song.mp3").exists()
    assert (workdir / "Others" / "weird.xyz").exists()


def test_organize_leaves_subfolders_and_hidden_files_alone(logger, workdir):
    write(workdir / "nested" / "photo.jpg")
    write(workdir / ".DS_Store")

    FileOrganizer(logger).organize_folder(str(workdir), ByFileType())

    assert (workdir / "nested" / "photo.jpg").exists()
    assert (workdir / ".DS_Store").exists()


def test_organize_does_not_overwrite_existing_file(logger, workdir):
    write(workdir / "Documents" / "doc.pdf", "old")
    write(workdir / "doc.pdf", "new")

    FileOrganizer(logger).organize_folder(str(workdir), ByFileType())

    assert (workdir / "Documents" / "doc.pdf").read_text() == "old"
    assert (workdir / "Documents" / "doc_1.pdf").read_text() == "new"


def test_organize_respects_excluded(logger, workdir):
    keep = write(workdir / "keep.pdf")

    FileOrganizer(logger, exclusion=ExclusionPolicy([str(keep)])).organize_folder(str(workdir), ByFileType())

    assert keep.exists()


def test_organize_is_undoable(logger, workdir):
    original = write(workdir / "doc.pdf")
    FileOrganizer(logger).organize_folder(str(workdir), ByFileType())

    ok, _ = logger.undo_last_action()

    assert ok
    assert original.exists()


def test_organize_by_month_uses_modified_date(logger, workdir):
    f = write(workdir / "old.txt")
    ts = datetime.datetime(2024, 3, 15).timestamp()
    os.utime(f, (ts, ts))

    FileOrganizer(logger).organize_folder(str(workdir), ByModifiedMonth())

    assert (workdir / "2024_03" / "old.txt").exists()


def test_organize_missing_folder(logger, workdir):
    ok, _ = FileOrganizer(logger).organize_folder(str(workdir / "nope"), ByFileType())
    assert not ok


def test_organize_file_already_in_place_is_skipped(logger, workdir):
    f = write(workdir / "Documents" / "doc.pdf")
    assert FileOrganizer(logger).organize_file(str(f), str(workdir / "Documents" / ".."), ByFileType()) is None
