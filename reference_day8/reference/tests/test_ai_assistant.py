from conftest import FakeLLM, write
from core.ai_assistant import AIAssistant


def test_scan_directory_lists_relative_paths(workdir, fake_llm):
    write(workdir / "a.txt")
    write(workdir / "sub" / "b.pdf")

    listing = AIAssistant(fake_llm).scan_directory(str(workdir))

    assert "- a.txt" in listing
    assert "sub/b.pdf" in listing.replace("\\", "/")


def test_scan_directory_skips_trash(workdir, fake_llm):
    write(workdir / ".zipzap_trash" / "deleted.txt")
    write(workdir / "kept.txt")

    listing = AIAssistant(fake_llm).scan_directory(str(workdir))

    assert "deleted.txt" not in listing
    assert "kept.txt" in listing


def test_scan_directory_stops_at_limit(workdir, fake_llm):
    for i in range(15):
        write(workdir / f"f{i}.txt")

    lines = AIAssistant(fake_llm).scan_directory(str(workdir), limit=10).splitlines()

    assert len(lines) == 11
    assert "10" in lines[-1]


def test_ask_ai_requires_key(workdir):
    assert "API Key" in AIAssistant(FakeLLM(configured=False)).ask_ai(str(workdir), "hi")


def test_ask_ai_requires_existing_folder(workdir, fake_llm):
    assert "โฟลเดอร์" in AIAssistant(fake_llm).ask_ai(str(workdir / "nope"), "hi")
    assert fake_llm.calls == []


def test_ask_ai_sends_file_list_and_question(workdir, fake_llm):
    fake_llm.reply = "budget.xlsx [OPEN: budget.xlsx]"
    write(workdir / "budget.xlsx")

    reply = AIAssistant(fake_llm).ask_ai(str(workdir), "where is my budget?")

    assert reply == "budget.xlsx [OPEN: budget.xlsx]"
    prompt, vision = fake_llm.calls[0]
    assert "budget.xlsx" in prompt
    assert "where is my budget?" in prompt
    assert vision is False


def test_ask_ai_returns_error_text_on_failure(workdir):
    reply = AIAssistant(FakeLLM(error="network down")).ask_ai(str(workdir), "hi")
    assert "network down" in reply
