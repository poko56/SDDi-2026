import contextlib
import datetime
import json
import os
import secrets
import shutil
import threading


class ActionLogger:
    """Writes a human-readable activity log and keeps a move history used by Undo."""

    def __init__(self, log_txt, log_json):
        self.log_txt = log_txt
        self.log_json = log_json
        # Cleaner, organizer and watcher threads may log at the same time
        self._lock = threading.Lock()
        # Each organize / cleaner run tags its moves with one batch id so Undo reverses them all together
        self._batch = threading.local()

    @contextlib.contextmanager
    def batch(self):
        """Tag every log_move() inside this block with one batch id, so Undo reverses the whole run."""
        self._batch.id = secrets.token_hex(8)
        try:
            yield
        finally:
            self._batch.id = None

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
                "batch_id": getattr(self._batch, "id", None),
            })
            self._write_moves(moves)
        self.log_action("MOVE/RENAME", f"From '{original_path}' -> '{new_path}'")

    def undo_last_action(self):
        """Reverse the last batch of moves (every file of one organize or cleaner run at once)."""
        with self._lock:
            if not os.path.exists(self.log_json):
                return False, "ไม่พบประวัติการทำงานใดๆ"
            moves = self._read_moves()
            if not moves:
                return False, "ไม่มีประวัติให้ย้อนกลับแล้ว"

            last_batch = moves[-1].get("batch_id")
            if last_batch:
                i = len(moves) - 1
                while i >= 0 and moves[i].get("batch_id") == last_batch:
                    i -= 1
                batch = moves[i + 1:]
                remaining = moves[:i + 1]
            else:
                batch = [moves[-1]]
                remaining = moves[:-1]

            reverted = 0
            skipped = []
            for entry in reversed(batch):  # Undo in reverse order of the moves
                original_path, new_path = entry["original_path"], entry["new_path"]
                try:
                    if not os.path.exists(new_path):
                        skipped.append(f"หาไฟล์ {os.path.basename(new_path)} ไม่พบ")
                        continue
                    if os.path.exists(original_path):
                        skipped.append(f"มีไฟล์ชื่อ {os.path.basename(original_path)} อยู่ที่เดิมแล้ว")
                        continue
                    os.makedirs(os.path.dirname(original_path), exist_ok=True)
                    shutil.move(new_path, original_path)
                    reverted += 1
                except OSError as e:
                    skipped.append(f"{os.path.basename(new_path)}: {e}")
            self._write_moves(remaining)

        self.log_action("UNDO", f"Reverted {reverted}/{len(batch)} files from the last batch")
        if reverted == 0:
            return False, "ย้อนกลับไม่ได้: " + (skipped[0] if skipped else "ไม่พบไฟล์")
        message = f"ย้อนกลับ {reverted} ไฟล์เรียบร้อย"
        if skipped:
            message += f" ({len(skipped)} ไฟล์ข้ามไป)"
        return True, message
