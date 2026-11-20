import sys
from pathlib import Path

from hub_app.config import GameEntry
from hub_app.launcher import (
    build_command,
    resolve_python,
    run_game,
    summarize_failure,
)


def make_game(game_dir: Path, python=None, entry: str = "main.py") -> GameEntry:
    return GameEntry(
        id="g",
        title="G",
        description="",
        dir=game_dir,
        entry=entry,
        thumbnail=None,
        python=python,
    )


def test_build_command_uses_python_and_entry():
    game = make_game(Path("/tmp/unused"), entry="play.py")

    assert build_command(game, "/usr/bin/python3") == ["/usr/bin/python3", "play.py"]


def test_resolve_python_uses_default_without_override(tmp_path):
    game = make_game(tmp_path)

    assert resolve_python(game, "/default/python") == "/default/python"


def test_resolve_python_prefers_game_override(tmp_path):
    override = tmp_path / "custom-python"
    game = make_game(tmp_path, python=override)

    assert resolve_python(game, "/default/python") == str(override)


def test_summarize_failure_uses_last_non_empty_stderr_line():
    stderr = "Traceback (most recent call last):\n  File x\nValueError: bad\n\n"

    assert summarize_failure(1, stderr) == "ValueError: bad"


def test_summarize_failure_truncates_long_lines():
    stderr = "E" * 200

    message = summarize_failure(1, stderr, max_len=120)

    assert len(message) == 120
    assert message.endswith("...")


def test_summarize_failure_falls_back_to_exit_code_when_stderr_empty():
    assert summarize_failure(3, "") == "Game exited with code 3"
    assert summarize_failure(3, "   \n\n") == "Game exited with code 3"


def test_run_game_missing_interpreter_fails_without_running(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')\n", encoding="utf-8")
    game = make_game(tmp_path)
    missing = str(tmp_path / "no-such-python")

    result = run_game(game, missing)

    assert result.ok is False
    assert result.returncode is None
    assert "Python interpreter not found" in result.message


def test_run_game_nonzero_exit_reports_failure(tmp_path):
    (tmp_path / "main.py").write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    game = make_game(tmp_path)

    result = run_game(game, sys.executable)

    assert result.ok is False
    assert result.returncode == 3
    assert result.message == "Game exited with code 3"


def test_run_game_zero_exit_reports_success(tmp_path):
    (tmp_path / "main.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    game = make_game(tmp_path)

    result = run_game(game, sys.executable)

    assert result.ok is True
    assert result.returncode == 0
