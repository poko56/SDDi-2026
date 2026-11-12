import hashlib
import os
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass

from core.exclusion import ExclusionPolicy
from core.file_types import is_junk
from core.paths import TRASH_DIR_NAME, unique_path

HASH_CHUNK_SIZE = 1024 * 1024
QUICK_HASH_SIZE = 64 * 1024


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
        """Only files sharing a size can be duplicates; confirm with a quick then a full SHA-256."""
        results = []
        for size, paths in paths_by_size.items():
            if len(paths) < 2:
                continue
            for candidates in self._group_by(paths, lambda p: self._hash(p, QUICK_HASH_SIZE)):
                if size > QUICK_HASH_SIZE:
                    groups = self._group_by(candidates, self._hash)
                else:
                    groups = [candidates]  # The quick hash already covered the whole file
                for group in groups:
                    # Prefer the one with the shortest basename (so "a.txt" beats "a (1).txt" and "a_copy.txt"),
                    # then the shallowest path, then alphabetical — a stable rule users can predict.
                    original = min(group, key=lambda p: (len(os.path.basename(p)), p.count(os.sep), p))
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
    def _hash(path, limit=None):
        hasher = hashlib.sha256()
        remaining = limit
        try:
            with open(path, "rb") as f:
                while remaining is None or remaining > 0:
                    chunk = f.read(HASH_CHUNK_SIZE if remaining is None else min(HASH_CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    hasher.update(chunk)
                    if remaining is not None:
                        remaining -= len(chunk)
        except OSError:
            return None
        return hasher.hexdigest()

    def clean_files(self, file_paths, root_folder):
        """Move files into <root_folder>/.zipzap_trash, keeping their relative path, so Undo can restore them."""
        trash_root = os.path.join(root_folder, TRASH_DIR_NAME)
        moved_bytes = 0
        moved_count = 0
        # Tag every move with one batch id so Undo restores the whole clean-up in one click
        with self.logger.batch():
            for path in file_paths:
                try:
                    size = os.path.getsize(path)
                    rel_path = os.path.relpath(path, root_folder)
                    if rel_path.startswith(".."):
                        rel_path = os.path.basename(path)
                    trash_path = unique_path(os.path.join(trash_root, rel_path))
                    os.makedirs(os.path.dirname(trash_path), exist_ok=True)
                    shutil.move(path, trash_path)
                except (OSError, ValueError) as e:
                    if os.path.exists(path):
                        self.logger.log_action("ERROR", f"Failed to move {path} to trash: {e}")
                    continue
                self.logger.log_move(path, trash_path)
                moved_bytes += size
                moved_count += 1

        self.logger.log_action("CLEAN_UP", f"Moved {moved_count} files ({moved_bytes} bytes) to {trash_root}")
        return moved_count, moved_bytes
