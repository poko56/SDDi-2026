import os
import shutil
from dataclasses import dataclass

from core.file_types import category_of
from core.paths import TRASH_DIR_NAME

DOCUMENT_CATEGORIES = {"Documents"}
MEDIA_CATEGORIES = {"Images", "Videos", "Audio"}


@dataclass
class StorageStats:
    file_count: int = 0
    documents_bytes: int = 0
    media_bytes: int = 0
    other_bytes: int = 0
    disk_free_bytes: int = 0

    @property
    def total_bytes(self):
        return self.documents_bytes + self.media_bytes + self.other_bytes


class StorageAnalyzer:
    """Adds up how much space each kind of file uses in a folder."""

    def analyze(self, folder_path, on_progress=None):
        """`on_progress(count)` is called periodically with the running file count, so the UI can show it."""
        stats = StorageStats()
        if not os.path.isdir(folder_path):
            return stats
        stack = [folder_path]
        next_report = 100
        while stack:
            try:
                with os.scandir(stack.pop()) as entries:
                    for entry in entries:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name != TRASH_DIR_NAME:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            self._add(stats, entry)
                            if on_progress is not None and stats.file_count >= next_report:
                                on_progress(stats.file_count)
                                next_report += 200  # Report every ~200 files
            except OSError:
                continue
        try:
            stats.disk_free_bytes = shutil.disk_usage(folder_path).free
        except OSError:
            pass
        return stats

    @staticmethod
    def _add(stats, entry):
        try:
            size = entry.stat(follow_symlinks=False).st_size
        except OSError:
            return
        stats.file_count += 1
        category = category_of(entry.name)
        if category in DOCUMENT_CATEGORIES:
            stats.documents_bytes += size
        elif category in MEDIA_CATEGORIES:
            stats.media_bytes += size
        else:
            stats.other_bytes += size
