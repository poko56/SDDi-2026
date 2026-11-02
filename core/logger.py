import datetime
import json
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

    def _read_moves(self):
        try:
            with open(self.log_json, "r", encoding="utf-8") as f:
                moves = json.load(f)
            return moves if isinstance(moves, list) else []
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_moves(self, moves):
        with open(self.log_json, "w", encoding="utf-8") as f:
            json.dump(moves, f, ensure_ascii=False, indent=4)

    def log_move(self, original_path, new_path):
        """Record a move/rename so undo_last_action() can reverse it."""
        with self._lock:
            moves = self._read_moves()
            moves.append({
                "timestamp": self.get_timestamp(),
                "original_path": original_path,
                "new_path": new_path,
            })
            self._write_moves(moves)
        self.log_action("MOVE/RENAME", f"From '{original_path}' -> '{new_path}'")
