import datetime
import os
import shutil

from core.exclusion import ExclusionPolicy
from core.file_types import category_of
from core.paths import unique_path


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
