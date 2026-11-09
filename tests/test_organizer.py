import datetime
import os

from PIL import Image

from conftest import FakeLLM, write
from core.exclusion import ExclusionPolicy
from core.organizer import ByFileType, ByModifiedMonth, FileOrganizer, sanitize_filename


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


def test_sanitize_filename():
    assert sanitize_filename(' Q3 "Sales"/Report?\n') == "Q3_SalesReport"
    assert sanitize_filename("../../etc/passwd") == "etcpasswd"
    assert sanitize_filename("   ") == ""
    assert len(sanitize_filename("a" * 500)) == 120


def test_smart_rename_requires_api_key(logger, workdir):
    f = write(workdir / "a.txt")
    ok, _ = FileOrganizer(logger, FakeLLM(configured=False)).smart_rename(str(f))
    assert not ok
    assert f.exists()


def test_smart_rename_rejects_unsupported_extension(logger, workdir, fake_llm):
    f = write(workdir / "a.docx")
    ok, _ = FileOrganizer(logger, fake_llm).smart_rename(str(f))
    assert not ok
    assert fake_llm.calls == []


def test_smart_rename_txt_sends_content_and_sanitises_reply(logger, workdir, fake_llm):
    f = write(workdir / "a.txt", "Quarterly report")
    fake_llm.reply = ' Q3 "Sales"/Report?\n'

    ok, new_name = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert (ok, new_name) == (True, "Q3_SalesReport.txt")
    assert (workdir / new_name).exists()
    contents, vision = fake_llm.calls[0]
    assert "Quarterly report" in contents[1]
    assert vision is True


def test_smart_rename_image_avoids_name_collision(logger, workdir, fake_llm):
    write(workdir / "Receipt.png", "existing")
    img = workdir / "IMG_0001.png"
    Image.new("RGB", (10, 10), "white").save(img)
    fake_llm.reply = "Receipt"

    ok, new_name = FileOrganizer(logger, fake_llm).smart_rename(str(img))

    assert (ok, new_name) == (True, "Receipt_1.png")
    assert (workdir / "Receipt.png").read_text() == "existing"


def test_smart_rename_pdf_uploads_then_deletes(logger, workdir, fake_llm):
    f = write(workdir / "scan.pdf")
    fake_llm.reply = "Invoice_1002"

    ok, _ = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert ok
    assert fake_llm.deleted == fake_llm.uploaded == [f"uploaded:{f}"]


def test_smart_rename_empty_reply_keeps_file(logger, workdir, fake_llm):
    f = write(workdir / "a.txt")
    fake_llm.reply = "   "

    ok, _ = FileOrganizer(logger, fake_llm).smart_rename(str(f))

    assert not ok
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
