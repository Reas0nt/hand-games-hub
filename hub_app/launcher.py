"""Run a game as a child process and summarize its outcome.

Pure module: no pygame, OpenCV or MediaPipe imports.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hub_app.config import GameEntry


@dataclass(frozen=True)
class LaunchResult:
    ok: bool
    returncode: int | None
    message: str


def resolve_python(game: GameEntry, default: str) -> str:
    if game.python is not None:
        return str(game.python)
    return default


def build_command(game: GameEntry, python: str) -> list[str]:
    return [python, game.entry]


def summarize_failure(returncode: int, stderr_text: str, max_len: int = 120) -> str:
    lines = [line.strip() for line in stderr_text.splitlines() if line.strip()]
    if not lines:
        return f"Game exited with code {returncode}"

    text = lines[-1]
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _interpreter_exists(python: str) -> bool:
    return Path(python).exists() or shutil.which(python) is not None


def run_game(game: GameEntry, default_python: str) -> LaunchResult:
    python = resolve_python(game, default_python)
    if not _interpreter_exists(python):
        return LaunchResult(False, None, f"Python interpreter not found: {python}")

    command = build_command(game, python)
    try:
        completed = subprocess.run(
            command,
            cwd=game.dir,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            check=False,
        )
    except OSError as exc:
        return LaunchResult(False, None, f"Could not start game: {exc}")

    if completed.returncode == 0:
        return LaunchResult(True, 0, "Game finished")

    message = summarize_failure(completed.returncode, completed.stderr or "")
    return LaunchResult(False, completed.returncode, message)
