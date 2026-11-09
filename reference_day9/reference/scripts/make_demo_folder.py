"""Create a folder of *real* files for demonstrating every ZipZap feature.

Usage (from the project root):
    python scripts/make_demo_folder.py             # creates ~/ZipZap_Demo
    python scripts/make_demo_folder.py --reset     # wipe and recreate it before another rehearsal
    python scripts/make_demo_folder.py /some/path  # somewhere else

Unlike TestFolder/, every file here opens properly, so Smart Rename, the
converters and audio extraction work on them.
"""
import argparse
import math
import os
import shutil
import sys
import time
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pillow_heif import register_heif_opener

register_heif_opener()

MARKER = ".zipzap_demo"
DEFAULT_TARGET = os.path.join(os.path.expanduser("~"), "ZipZap_Demo")
FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def draw_document(lines, size=(700, 900), title_size=40, body_size=26):
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    y = 50
    for i, line in enumerate(lines):
        font = load_font(title_size if i == 0 else body_size)
        draw.text((50, y), line, fill="black", font=font)
        y += title_size + 30 if i == 0 else body_size + 18
    return img


def make_receipt(path):
    draw_document([
        "STARBUCKS COFFEE",
        "Siam Paragon, Bangkok",
        "Date: 2026-03-14  10:42",
        "",
        "Caffe Latte (Grande)      145.00",
        "Butter Croissant           95.00",
        "",
        "TOTAL                     240.00 THB",
        "Paid by: Visa",
    ], size=(640, 700)).save(path)


def make_invoice_pdf(path):
    draw_document([
        "INVOICE #INV-2026-0042",
        "Bill to: KMITL Software Engineering Club",
        "Issue date: 2026-09-01",
        "",
        "Web hosting (12 months)      3,600.00",
        "Domain name renewal            450.00",
        "",
        "TOTAL DUE                    4,050.00 THB",
        "Due date: 2026-09-30",
    ]).save(path, "PDF", resolution=100)


def make_photo(path):
    """A simple sunset-style landscape (gradient sky, sun, sea)."""
    width, height = 800, 533
    sky = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        t = y / height
        sky[y, :] = (int(255 - 60 * t), int(140 + 60 * t), int(60 + 160 * t))
    img = Image.fromarray(sky)
    draw = ImageDraw.Draw(img)
    draw.ellipse((330, 150, 470, 290), fill=(255, 210, 90))
    draw.rectangle((0, 330, width, height), fill=(30, 90, 140))
    draw.text((20, 20), "Phuket beach trip - Dec 2025", fill="white", font=load_font(30))
    try:
        img.save(path)  # .heic via pillow-heif
    except (OSError, ValueError, KeyError):
        path = os.path.splitext(path)[0] + ".jpg"
        img.save(path)
    return path


def make_docx(path, paragraphs):
    """Minimal but valid .docx (enough for Word and docx2pdf)."""
    body = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{p}</w:t></w:r></w:p>" for p in paragraphs)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)


def tone(freq, duration, fps=44100):
    from moviepy import AudioClip

    def frame(t):
        wave = 0.3 * np.sin(2 * math.pi * freq * np.asarray(t))
        return np.column_stack([wave, wave])
    return AudioClip(frame, duration=duration, fps=fps)


def make_mp3(path):
    tone(440, 3).write_audiofile(path, fps=44100, logger=None)


def make_video(path):
    from moviepy import ColorClip

    clip = ColorClip(size=(320, 240), color=(124, 58, 237), duration=3).with_audio(tone(660, 3))
    clip.write_videofile(path, fps=24, codec="libx264", audio_codec="aac", logger=None)


def make_large_old_file(path, size_mb=60, days_old=90):
    """A sparse file: reports 60MB but uses almost no disk space."""
    with open(path, "wb") as f:
        f.truncate(size_mb * 1024 * 1024)
    old = time.time() - days_old * 24 * 3600
    os.utime(path, (old, old))


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build(target):
    os.makedirs(os.path.join(target, "Backup"), exist_ok=True)
    write_text(os.path.join(target, MARKER), "Created by scripts/make_demo_folder.py\n")
    p = lambda *parts: os.path.join(target, *parts)  # noqa: E731

    make_receipt(p("IMG_0001.png"))
    photo = make_photo(p("IMG_0002.heic"))
    make_invoice_pdf(p("scan_001.pdf"))
    write_text(p("note1.txt"),
               "บันทึกการประชุมทีม ZipZap\nวันที่ 20 ตุลาคม 2569\n"
               "- สรุปแผนการนำเสนอโครงงานวันพฤหัสบดี\n- แบ่งงานทำสไลด์ Threat Model และ CI/CD\n")
    write_text(p("data.csv"), "month,income,expense\nJan,12000,8000\nFeb,12500,9100\nMar,13000,8700\n")
    make_docx(p("project_report.docx"),
              ["ZipZap Project Report", "Software Design and Development 2",
               "This report describes the architecture of ZipZap."])
    make_mp3(p("voice_memo.mp3"))
    make_video(p("screen_record.mp4"))

    # Duplicates (same bytes in another folder) for the Smart Cleaner
    shutil.copy2(p("IMG_0001.png"), p("Backup", "IMG_0001_copy.png"))
    shutil.copy2(p("scan_001.pdf"), p("Backup", "scan_001 (1).pdf"))

    # Junk files
    write_text(p("cache.tmp"), "temporary cache data\n")
    write_text(p("debug.log"), "[DEBUG] app started\n" * 50)
    write_text(p("Backup", "old_settings.bak"), "backup\n")

    # Large & unused (60MB, last modified 90 days ago)
    make_large_old_file(p("old_backup.zip"))
    return os.path.basename(photo)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=DEFAULT_TARGET)
    parser.add_argument("--reset", action="store_true", help="delete and recreate an existing demo folder")
    args = parser.parse_args()
    target = os.path.abspath(args.target)

    if os.path.exists(target):
        if not args.reset:
            sys.exit(f"{target} already exists. Use --reset to recreate it.")
        if not os.path.exists(os.path.join(target, MARKER)):
            sys.exit(f"Refusing to delete {target}: it was not created by this script.")
        shutil.rmtree(target)

    photo_name = build(target)
    print(f"Demo folder ready: {target}")
    print(f"  Smart Rename : IMG_0001.png (receipt), {photo_name} (photo), scan_001.pdf, note1.txt (Thai)")
    print("  Converter    : project_report.docx -> PDF, IMG_0002 -> JPG, screen_record.mp4 -> MP3")
    print("  Cleaner      : 2 duplicates in Backup/, 3 junk files, old_backup.zip (60MB, 90 days old)")
    print("  Organize     : the loose files in the top folder")


if __name__ == "__main__":
    main()
