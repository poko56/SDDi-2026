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

    def analyze(self, folder_path):
        stats = StorageStats()
        if not os.path.isdir(folder_path):
            return stats
        stack = [folder_path]
        while stack:
            try:
                with os.scandir(stack.pop()) as entries:
                    for entry in entries:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name != TRASH_DIR_NAME:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            self._add(stats, entry)
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
