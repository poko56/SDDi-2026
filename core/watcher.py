import os
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from core.exclusion import ExclusionPolicy
from core.paths import TRASH_DIR_NAME

CONVERT_FOLDER_NAME = "Convert_to_PDF"
SETTLE_SECONDS = 2  # Wait for the file to finish copying before touching it


class SmartFileHandler(FileSystemEventHandler):
    """Reacts to files appearing in the watched folder.

    New top-level files go to `on_new_file`; .docx files dropped into
    Convert_to_PDF/ go to `on_pdf_convert`. Each path is handled once per burst
    of events (a debounce timer), and files the app itself moves into
    sub-folders are ignored so sorting does not trigger more sorting.
    """

    def __init__(self, root, logger, callbacks, exclusion=None, settle_seconds=SETTLE_SECONDS):
        self.root = os.path.abspath(root)
        self.logger = logger
        self.callbacks = callbacks
        self.exclusion = exclusion or ExclusionPolicy()
        self.settle_seconds = settle_seconds
        self._timers = {}
        self._lock = threading.Lock()

    def _schedule(self, path):
        with self._lock:
            old = self._timers.pop(path, None)
            if old:
                old.cancel()
            timer = threading.Timer(self.settle_seconds, self._fire, args=(path,))
            timer.daemon = True
            self._timers[path] = timer
            timer.start()

    def _fire(self, path):
        with self._lock:
            self._timers.pop(path, None)
        self.process_file(path)

    def cancel_pending(self):
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()

    def process_file(self, file_path):
        if self.exclusion.is_excluded(file_path) or not os.path.isfile(file_path):
            return
        try:
            if os.path.getsize(file_path) == 0:
                return
        except OSError:
            return

        parent = os.path.dirname(os.path.abspath(file_path))
        name = os.path.basename(file_path)
        if os.path.basename(parent) == CONVERT_FOLDER_NAME:
            if name.lower().endswith(".docx") and "on_pdf_convert" in self.callbacks:
                self.logger.log_action("WATCHER", f"Detected {name} in {CONVERT_FOLDER_NAME}. Converting.")
                self.callbacks["on_pdf_convert"](file_path)
        elif parent == self.root and not name.startswith("."):
            if "on_new_file" in self.callbacks:
                self.logger.log_action("WATCHER", f"Detected new file {name}. Auto-sorting.")
                self.callbacks["on_new_file"](file_path)

    def _relevant(self, path):
        return TRASH_DIR_NAME not in path.split(os.sep)

    def on_created(self, event):
        if not event.is_directory and self._relevant(event.src_path):
            self._schedule(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and self._relevant(event.dest_path):
            self._schedule(event.dest_path)


class WatcherManager:
    def __init__(self, logger, exclusion=None):
        self.logger = logger
        self.exclusion = exclusion or ExclusionPolicy()
        self.observer = None
        self._handler = None

    @property
    def is_running(self):
        return self.observer is not None

    def start_watching(self, path, callbacks):
        if not os.path.isdir(path):
            return False, "ไม่พบโฟลเดอร์เป้าหมาย"
        if self.observer is not None:
            self.stop_watching()
        os.makedirs(os.path.join(path, CONVERT_FOLDER_NAME), exist_ok=True)

        self._handler = SmartFileHandler(path, self.logger, callbacks, self.exclusion)
        self.observer = Observer()
        self.observer.schedule(self._handler, path, recursive=True)
        self.observer.start()
        self.logger.log_action("WATCHER_START", f"Started monitoring {path}")
        return True, f"ระบบเริ่มจับตาดูการเปลี่ยนแปลงในโฟลเดอร์ {path} แล้ว"

    def stop_watching(self):
        if self.observer is None:
            return False, "ระบบไม่ได้เปิดทำงานอยู่"
        self._handler.cancel_pending()
        self.observer.stop()
        self.observer.join()
        self.observer = None
        self._handler = None
        self.logger.log_action("WATCHER_STOP", "Stopped monitoring")
        return True, "หยุดระบบจับตาดูโฟลเดอร์แล้ว"
