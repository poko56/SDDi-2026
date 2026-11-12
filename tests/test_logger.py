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


def test_undo_reverses_a_whole_batch_in_one_call(logger, workdir):
    """Organize and clean tag every move with one batch id; one Undo click must restore them all."""
    sources = [write(workdir / f"a{i}.txt") for i in range(3)]
    dests = [workdir / "sub" / f"a{i}.txt" for i in range(3)]
    dests[0].parent.mkdir()

    with logger.batch():
        for src, dst in zip(sources, dests):
            src.rename(dst)
            logger.log_move(str(src), str(dst))

    ok, message = logger.undo_last_action()

    assert ok
    assert "3" in message
    for src, dst in zip(sources, dests):
        assert src.exists()
        assert not dst.exists()


def test_undo_reverses_only_the_last_batch(logger, workdir):
    """Earlier batches stay on the stack so later Undo clicks can roll them back too."""
    first = write(workdir / "first.txt")
    first_dst = workdir / "sub1" / "first.txt"
    first_dst.parent.mkdir()
    with logger.batch():
        first.rename(first_dst)
        logger.log_move(str(first), str(first_dst))

    second = [write(workdir / f"s{i}.txt") for i in range(2)]
    second_dsts = [workdir / "sub2" / f"s{i}.txt" for i in range(2)]
    second_dsts[0].parent.mkdir()
    with logger.batch():
        for src, dst in zip(second, second_dsts):
            src.rename(dst)
            logger.log_move(str(src), str(dst))

    logger.undo_last_action()  # Only the second batch

    assert first_dst.exists() and not first.exists()
    for src, dst in zip(second, second_dsts):
        assert src.exists() and not dst.exists()


def test_undo_preserves_legacy_single_file_history(logger, workdir):
    """Old entries written before batches existed still behave as one-file undos."""
    original = write(workdir / "x.txt")
    moved = workdir / "sub" / "x.txt"
    moved.parent.mkdir()
    original.rename(moved)
    logger.log_move(str(original), str(moved))  # No batch() context → batch_id is None

    ok, _ = logger.undo_last_action()

    assert ok
    assert original.exists()
