import hashlib
import os
import time
from collections import defaultdict
from dataclasses import dataclass

from core.exclusion import ExclusionPolicy
from core.file_types import is_junk
from core.paths import TRASH_DIR_NAME

HASH_CHUNK_SIZE = 1024 * 1024


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
        by_size = defaultdict(list)
        min_large_bytes = options.large_min_mb * 1024 * 1024
        cutoff = time.time() - options.large_min_days * 24 * 3600

        for path, st in self._iter_files(folder_path):
            if options.junk and is_junk(path):
                results.append(ScanResult(path, st.st_size, "junk"))
            if options.large and st.st_size > min_large_bytes and st.st_mtime < cutoff:
                results.append(ScanResult(path, st.st_size, "large"))
            if options.duplicates and st.st_size > 0:
                by_size[st.st_size].append(path)

        if options.duplicates:
            results.extend(self._find_duplicates(by_size))
        return results

    def _find_duplicates(self, paths_by_size):
        """Only files sharing a size can be duplicates; confirm with a full SHA-256."""
        results = []
        for size, paths in paths_by_size.items():
            if len(paths) < 2:
                continue
            for group in self._group_by(paths, self._hash):
                original = min(group, key=lambda p: (p.count(os.sep), p))
                results.extend(
                    ScanResult(p, size, "duplicate", original) for p in group if p != original
                )
        return results

    @staticmethod
    def _group_by(paths, key_func):
        groups = defaultdict(list)
        for path in paths:
            key = key_func(path)
            if key is not None:
                groups[key].append(path)
        return [g for g in groups.values() if len(g) > 1]

    @staticmethod
    def _hash(path):
        hasher = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(HASH_CHUNK_SIZE)
                    if not chunk:
                        break
                    hasher.update(chunk)
        except OSError:
            return None
        return hasher.hexdigest()
