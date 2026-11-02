import json


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
