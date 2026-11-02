import json

from conftest import write


def test_log_action_appends_line(logger):
    logger.log_action("TEST", "hello")
    logger.log_action("TEST", "world")

    with open(logger.log_txt, encoding="utf-8") as f:
        lines = f.read().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("TEST: hello")


def test_log_move_records_json_entry(logger, workdir):
    logger.log_move(str(workdir / "a.txt"), str(workdir / "b.txt"))

    with open(logger.log_json, encoding="utf-8") as f:
        entries = json.load(f)
    assert entries[-1]["original_path"] == str(workdir / "a.txt")
    assert entries[-1]["new_path"] == str(workdir / "b.txt")


def test_undo_moves_file_back(logger, workdir):
    original = write(workdir / "a.txt")
    moved = workdir / "sub" / "a.txt"
    moved.parent.mkdir()
    original.rename(moved)
    logger.log_move(str(original), str(moved))

    ok, _ = logger.undo_last_action()

    assert ok
    assert original.exists()
    assert not moved.exists()


def test_undo_without_history(logger):
    ok, _ = logger.undo_last_action()
    assert not ok


def test_undo_when_moved_file_is_gone(logger, workdir):
    logger.log_move(str(workdir / "a.txt"), str(workdir / "missing.txt"))

    ok, _ = logger.undo_last_action()

    assert not ok
    # The broken entry is dropped so the next undo does not retry it forever
    with open(logger.log_json, encoding="utf-8") as f:
        assert json.load(f) == []


def test_undo_with_corrupt_json(logger):
    with open(logger.log_json, "w", encoding="utf-8") as f:
        f.write("{not json")

    ok, _ = logger.undo_last_action()
    assert not ok
