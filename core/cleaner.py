import os
from dataclasses import dataclass

from core.exclusion import ExclusionPolicy
from core.file_types import is_junk
from core.paths import TRASH_DIR_NAME


@dataclass
class ScanOptions:
    duplicates: bool = True
    junk: bool = True
    large: bool = False
    large_min_mb: float = 50
    large_min_days: int = 30


@dataclass
class ScanResult:
    path: str
    size: int
    type: str  # "duplicate" | "junk" | "large"
    original: str = ""  # For duplicates: the copy that is kept


class StorageCleaner:
    """Finds duplicate, junk and large unused files and moves chosen ones to a trash folder."""

    def __init__(self, logger, exclusion=None):
        self.logger = logger
        self.exclusion = exclusion or ExclusionPolicy()

    def _iter_files(self, folder_path):
        """Yield (path, os.stat_result) for every file, skipping the trash and excluded folders."""
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [
                d for d in dirs
                if d != TRASH_DIR_NAME and not self.exclusion.is_excluded(os.path.join(root, d))
            ]
            for name in files:
                path = os.path.join(root, name)
                if self.exclusion.is_excluded(path):
                    continue
                try:
                    yield path, os.stat(path)
                except OSError:
                    continue

    def scan(self, folder_path, options=None):
        """Walk the folder once and return a list of ScanResult for every enabled check."""
        options = options or ScanOptions()
        if not os.path.isdir(folder_path):
            return []

        results = []
        for path, st in self._iter_files(folder_path):
            if options.junk and is_junk(path):
                results.append(ScanResult(path, st.st_size, "junk"))
        return results
