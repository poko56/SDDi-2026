import datetime
import threading


class ActionLogger:
    """Writes a human-readable activity log and keeps a move history used by Undo."""

    def __init__(self, log_txt, log_json):
        self.log_txt = log_txt
        self.log_json = log_json
        # Cleaner, organizer and watcher threads may log at the same time
        self._lock = threading.Lock()

    @staticmethod
    def get_timestamp():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_action(self, action_type, details):
        entry = f"[{self.get_timestamp()}] {action_type}: {details}\n"
        with self._lock:
            try:
                with open(self.log_txt, "a", encoding="utf-8") as f:
                    f.write(entry)
            except OSError:
                # Logging must never break the operation being logged
                pass
