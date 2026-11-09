import datetime
import os
import re
import shutil

from PIL import Image
from pillow_heif import register_heif_opener

from core.exclusion import ExclusionPolicy
from core.file_types import category_of, extension_of
from core.llm import AINotConfiguredError, AIServiceError
from core.paths import unique_path

register_heif_opener()

RENAME_PROMPT = (
    "Please analyze this file and suggest a concise, meaningful filename (without extension). "
    "If the document or content is mainly in Thai, the filename MUST be in Thai. "
    "Use format like YYYYMMDD_Topic or just a descriptive name. Use underscores (_) instead of spaces. "
    "Thai dates often use the Buddhist Era (พ.ศ.): subtract 543 to get the year for YYYYMMDD "
    "(for example พ.ศ. 2569 is 2026). "
    "Do not use special characters. Reply ONLY with the suggested filename and nothing else."
)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
RENAMEABLE_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".txt"}
_UNSAFE_FILENAME_CHARS = re.compile(r"[<>:\"/\\|?*`'\x00-\x1f]")
MAX_NAME_LENGTH = 120
MAX_TEXT_CHARS = 5000
PDF_TEXT_PAGES = 3
NOT_CONFIGURED_MESSAGE = "กรุณาตั้งค่า AI ในหน้า Settings ก่อน (ใส่ Gemini API Key หรือเลือกโมเดล Local AI)"


class SortStrategy:
    """Decides which sub-folder a file belongs in. Add a subclass to add a new way to organize."""

    label = ""

    def folder_for(self, path):
        raise NotImplementedError


class ByFileType(SortStrategy):
    label = "ประเภทไฟล์"

    def folder_for(self, path):
        return category_of(path)


class ByModifiedMonth(SortStrategy):
    label = "เดือนที่แก้ไข"

    def folder_for(self, path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y_%m")


def sanitize_filename(name):
    name = name.strip().replace("\r", "").replace("\n", "").replace(" ", "_")
    name = _UNSAFE_FILENAME_CHARS.sub("", name).strip("._")
    return name[:MAX_NAME_LENGTH]


class FileOrganizer:
    def __init__(self, logger, llm=None, exclusion=None):
        self.logger = logger
        self.llm = llm
        self.exclusion = exclusion or ExclusionPolicy()

    def organize_file(self, file_path, root_folder, strategy):
        """Move one file into <root_folder>/<strategy folder>/. Returns the new path, or None if skipped."""
        if not os.path.isfile(file_path) or self.exclusion.is_excluded(file_path):
            return None
        target_dir = os.path.join(root_folder, strategy.folder_for(file_path))
        if os.path.dirname(os.path.abspath(file_path)) == os.path.abspath(target_dir):
            return None
        os.makedirs(target_dir, exist_ok=True)
        new_path = unique_path(os.path.join(target_dir, os.path.basename(file_path)))
        shutil.move(file_path, new_path)
        self.logger.log_move(file_path, new_path)
        return new_path

    def organize_folder(self, folder_path, strategy):
        """Organize the files directly inside folder_path (sub-folders are left alone)."""
        if not os.path.isdir(folder_path):
            return False, "ไม่พบโฟลเดอร์ที่ระบุ"
        moved, failed = 0, 0
        with os.scandir(folder_path) as entries:
            files = [e.path for e in entries if e.is_file() and not e.name.startswith(".")]
        for path in files:
            try:
                if self.organize_file(path, folder_path, strategy):
                    moved += 1
            except OSError as e:
                failed += 1
                self.logger.log_action("ERROR", f"Failed to organize {path}: {e}")
        message = f"จัดไฟล์ตาม{strategy.label}สำเร็จ {moved} ไฟล์"
        if failed:
            message += f" (ย้ายไม่ได้ {failed} ไฟล์)"
        return True, message

    def _build_rename_prompt(self, file_path, ext):
        """Return (contents, uploaded_file_or_None) for the AI request."""
        if ext in IMAGE_EXTENSIONS:
            with Image.open(file_path) as img:
                img.load()
                return [RENAME_PROMPT, img.copy()], None
        if ext == ".pdf":
            uploaded = self.llm.upload_file(file_path)
            return [uploaded, RENAME_PROMPT], uploaded
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read(MAX_TEXT_CHARS)
        return [RENAME_PROMPT, f"File content:\n{text}"], None

    def smart_rename(self, file_path):
        """Ask the AI for a meaningful name and rename the file. Returns (ok, new_name_or_error)."""
        if self.llm is None or not self.llm.is_configured:
            return False, NOT_CONFIGURED_MESSAGE
        ext = extension_of(file_path)
        if ext not in RENAMEABLE_EXTENSIONS:
            return False, f"ฟังก์ชันนี้ยังไม่รองรับไฟล์นามสกุล {ext}"

        uploaded = None
        try:
            contents, uploaded = self._build_rename_prompt(file_path, ext)
            suggestion = self.llm.generate(contents, vision=True)
        except AINotConfiguredError:
            return False, NOT_CONFIGURED_MESSAGE
        except AIServiceError as e:
            if "INVALID_ARGUMENT" in str(e):
                return False, ("ไฟล์นี้อาจเป็นไฟล์จำลอง (Fake file) หรือไฟล์เสียหาย "
                               "AI จึงไม่สามารถอ่านเนื้อหาข้างในได้ครับ")
            return False, f"เชื่อมต่อ AI ไม่สำเร็จ: {e}"
        except OSError as e:
            return False, f"อ่านไฟล์ไม่ได้: {e}"
        finally:
            if uploaded is not None:
                self.llm.delete_file(uploaded)

        new_stem = sanitize_filename(suggestion)
        if not new_stem:
            return False, "AI ไม่ได้เสนอชื่อไฟล์ใหม่"
        old_name = os.path.basename(file_path)
        new_name = new_stem + ext
        if new_name == old_name:
            return False, "ชื่อเดิมสื่อความหมายอยู่แล้ว ไม่ต้องเปลี่ยน"
        new_path = os.path.join(os.path.dirname(file_path), new_name)
        if new_name.lower() != old_name.lower():
            # A case-only change must not count the file itself as a name clash (macOS/Windows ignore case)
            new_path = unique_path(new_path)
        try:
            shutil.move(file_path, new_path)
        except OSError as e:
            return False, f"เปลี่ยนชื่อไม่สำเร็จ: {e}"
        self.logger.log_move(file_path, new_path)
        return True, os.path.basename(new_path)
