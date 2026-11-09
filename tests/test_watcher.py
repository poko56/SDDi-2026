import threading

from conftest import write
from core.exclusion import ExclusionPolicy
from core.watcher import CONVERT_FOLDER_NAME, SmartFileHandler


class Event:
    def __init__(self, src_path, dest_path=None, is_directory=False):
        self.src_path = src_path
        self.dest_path = dest_path
        self.is_directory = is_directory


def make_handler(root, logger, excluded=None, settle_seconds=0):
    calls = {"sort": [], "pdf": []}
    callbacks = {"on_new_file": calls["sort"].append, "on_pdf_convert": calls["pdf"].append}
    handler = SmartFileHandler(str(root), logger, callbacks, ExclusionPolicy(excluded), settle_seconds)
    return handler, calls


def test_new_top_level_file_triggers_auto_sort(logger, workdir):
    f = write(workdir / "a.jpg")
    handler, calls = make_handler(workdir, logger)

    handler.process_file(str(f))

    assert calls == {"sort": [str(f)], "pdf": []}


def test_files_in_subfolders_are_not_resorted(logger, workdir):
    f = write(workdir / "Images" / "a.jpg")
    handler, calls = make_handler(workdir, logger)

    handler.process_file(str(f))

    assert calls == {"sort": [], "pdf": []}


def test_docx_in_convert_folder_triggers_pdf(logger, workdir):
    f = write(workdir / CONVERT_FOLDER_NAME / "a.docx")
    handler, calls = make_handler(workdir, logger)

    handler.process_file(str(f))

    assert calls == {"sort": [], "pdf": [str(f)]}


def test_ignores_empty_missing_hidden_and_excluded_files(logger, workdir):
    empty = workdir / "empty.txt"
    empty.write_text("")
    hidden = write(workdir / ".DS_Store")
    private = write(workdir / "private.txt")
    handler, calls = make_handler(workdir, logger, excluded=[str(private)])

    for path in (empty, hidden, workdir / "ghost.txt", private):
        handler.process_file(str(path))

    assert calls == {"sort": [], "pdf": []}


def test_burst_of_events_is_handled_once(logger, workdir):
    f = write(workdir / "a.jpg")
    handled = threading.Event()
    calls = []

    def on_new_file(path):
        calls.append(path)
        handled.set()

    handler = SmartFileHandler(str(workdir), logger, {"on_new_file": on_new_file}, settle_seconds=0.2)
    for _ in range(5):
        handler.on_created(Event(str(f)))

    assert handled.wait(2)
    handler.cancel_pending()
    assert calls == [str(f)]


def test_trash_and_directory_events_are_ignored(logger, workdir):
    handler, calls = make_handler(workdir, logger)
    handler.on_created(Event(str(workdir / ".zipzap_trash" / "a.tmp")))
    handler.on_created(Event(str(workdir / "newdir"), is_directory=True))
    assert handler._timers == {}
