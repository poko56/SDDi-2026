"""Single source of truth for which extensions belong to which category."""
import os

CATEGORY_EXTENSIONS = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx", ".csv"},
    "Audio": {".mp3", ".wav", ".aac", ".flac"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
}
OTHER_CATEGORY = "Others"

JUNK_EXTENSIONS = {".tmp", ".log", ".cache", ".bak", ".dat"}

_EXTENSION_TO_CATEGORY = {
    ext: category for category, exts in CATEGORY_EXTENSIONS.items() for ext in exts
}


def extension_of(path):
    return os.path.splitext(path)[1].lower()


def category_of(path):
    return _EXTENSION_TO_CATEGORY.get(extension_of(path), OTHER_CATEGORY)


def is_junk(path):
    return extension_of(path) in JUNK_EXTENSIONS


def format_size(size_in_bytes):
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 ** 2:
        return f"{size_in_bytes / 1024:.1f} KB"
    if size_in_bytes < 1024 ** 3:
        return f"{size_in_bytes / 1024 ** 2:.1f} MB"
    return f"{size_in_bytes / 1024 ** 3:.2f} GB"
