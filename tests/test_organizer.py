import datetime
import os

import pytest
from PIL import Image

from conftest import FakeLLM, write
from core.exclusion import ExclusionPolicy
from core.organizer import ByFileType, ByModifiedMonth, FileOrganizer, annotate_buddhist_years, sanitize_filename


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
    assert not (workdir / "Documents" / "doc.pdf").exists()


def test_organize_by_month(logger, workdir):
    f = write(workdir / "doc.pdf")
    dt = datetime.datetime(2026, 3, 14, 12, 0, 0).timestamp()
    os.utime(f, (dt, dt))

    FileOrganizer(logger).organize_folder(str(workdir), ByModifiedMonth())

    assert (workdir / "2026-03" / "doc.pdf").exists()


# ---------- Smart Rename ----------

def test_sanitize_filename():
    assert sanitize_filename(' bad/file:name*? "ok" <yes>| ') == "bad_file_name_ok_yes"
    assert sanitize_filename("") == "renamed_file"


def test_smart_rename_text_file(logger, workdir, fake_llm):
    f = write(workdir / "notes.txt", "Project proposal draft")
    fake_llm.reply = "Proposal_Draft"

    ok, new_name = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert (ok, new_name) == (True, "Proposal_Draft.txt")
    assert (workdir / "Proposal_Draft.txt").exists()
    assert not f.exists()


def test_smart_rename_image_sends_image_object_to_ai(logger, workdir, fake_llm):
    f = workdir / "photo.jpg"
    Image.new("RGB", (100, 100), "red").save(f)
    fake_llm.reply = "Red_Square"

    FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert fake_llm.calls[0][1] is True
    assert isinstance(fake_llm.calls[0][0][1], Image.Image)


def test_smart_rename_pdf_uses_file_upload(logger, workdir, fake_llm):
    f = write(workdir / "receipt.pdf", "dummy pdf content")
    fake_llm.reply = "Starbucks_Receipt"

    ok, new_name = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert (ok, new_name) == (True, "Starbucks_Receipt.pdf")
    assert fake_llm.uploaded == [f"uploaded:{f}"]
    assert fake_llm.deleted == [f"uploaded:{f}"]


def test_smart_rename_cleans_deleted_file_when_generation_fails(logger, workdir):
    f = write(workdir / "receipt.pdf", "dummy")
    llm = FakeLLM(error="rate limit")

    ok, _ = FileOrganizer(logger, llm).smart_rename(str(f))

    assert not ok
    assert llm.deleted == [f"uploaded:{f}"]


def test_smart_rename_without_api_key(logger, workdir):
    f = write(workdir / "a.txt")
    llm = FakeLLM(configured=False)

    ok, msg = FileOrganizer(logger, llm).smart_rename(str(f))

    assert not ok
    assert "ตั้งค่า Gemini API key" in msg


def test_smart_rename_reports_quota_error(logger, workdir):
    f = write(workdir / "a.txt")
    ok, msg = FileOrganizer(logger, FakeLLM(error="429 RESOURCE_EXHAUSTED")).smart_rename(str(f))
    assert not ok
    assert "โควตา API เต็ม" in msg
    assert f.exists()


def test_smart_rename_reports_invalid_file(logger, workdir):
    f = write(workdir / "a.txt")
    ok, msg = FileOrganizer(logger, FakeLLM(error="400 INVALID_ARGUMENT")).smart_rename(str(f))
    assert not ok
    assert "Fake file" in msg
    assert f.exists()


def test_smart_rename_is_undoable(logger, workdir, fake_llm):
    f = write(workdir / "a.txt")
    FileOrganizer(logger, fake_llm).smart_rename(str(f))

    ok, _ = logger.undo_last_action()

    assert ok
    assert f.exists()


def test_smart_rename_same_name_is_left_alone(logger, workdir, fake_llm):
    f = write(workdir / "notes.txt")
    fake_llm.reply = "notes"

    ok, msg = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert not ok
    assert "ชื่อเดิม" in msg
    assert sorted(p.name for p in workdir.iterdir()) == ["notes.txt"]


def test_smart_rename_case_only_change(logger, workdir, fake_llm):
    f = write(workdir / "notes.txt")
    fake_llm.reply = "Notes"

    ok, new_name = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert (ok, new_name) == (True, "Notes.txt")
    assert sorted(p.name for p in workdir.iterdir()) == ["Notes.txt"]


@pytest.mark.parametrize("text, expected", [
    ("วันที่ 20 ตุลาคม 2569", "วันที่ 20 ตุลาคม 2569 (ค.ศ. 2026)"),
    ("พ.ศ. 2568", "พ.ศ. 2568 (ค.ศ. 2025)"),
    ("1 ต.ค. 2569", "1 ต.ค. 2569 (ค.ศ. 2026)"),
    ("ราคา 2569 บาท", "ราคา 2569 บาท"),
    ("October 2026", "October 2026"),
])
def test_annotate_buddhist_years(text, expected):
    assert annotate_buddhist_years(text) == expected


def test_smart_rename_sends_gregorian_year_hint(logger, workdir, fake_llm):
    f = write(workdir / "note.txt", "ประชุมวันที่ 20 ตุลาคม 2569")
    FileOrganizer(logger, fake_llm).smart_rename(str(f))
    assert "ค.ศ. 2026" in fake_llm.calls[0][0][1]
