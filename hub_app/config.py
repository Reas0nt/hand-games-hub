"""Load and validate the game catalogue from games.json.

Pure module: no pygame, OpenCV or MediaPipe imports.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when games.json is missing, malformed or points at missing files."""


@dataclass(frozen=True)
class GameEntry:
    id: str
    title: str
    description: str
    dir: Path
    entry: str
    thumbnail: Path | None
    python: Path | None


def _require_str(item: dict[str, Any], key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"games[{index}]: '{key}' must be a non-empty string")
    return value


def _optional_str(item: dict[str, Any], key: str, index: int) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"games[{index}]: '{key}' must be a string or null")
    return value


def parse_games(data: Any, hub_root: Path) -> list[GameEntry]:
    """Validate the parsed games.json content and build GameEntry objects."""
    if not isinstance(data, dict) or "games" not in data:
        raise ConfigError("games.json must contain a top-level 'games' list")

    raw_games = data["games"]
    if not isinstance(raw_games, list) or not raw_games:
        raise ConfigError("'games' must be a non-empty list")

    seen_ids: set[str] = set()
    games: list[GameEntry] = []

    for index, item in enumerate(raw_games):
        if not isinstance(item, dict):
            raise ConfigError(f"games[{index}] must be an object")

        game_id = _require_str(item, "id", index)
        if game_id in seen_ids:
            raise ConfigError(f"Duplicate game id: '{game_id}'")
        seen_ids.add(game_id)

        title = _require_str(item, "title", index)
        description = _optional_str(item, "description", index) or ""
        entry_name = _require_str(item, "entry", index)
        game_dir = (hub_root / _require_str(item, "dir", index)).resolve()

        if not game_dir.is_dir():
            raise ConfigError(f"games[{index}]: directory not found: {game_dir}")
        if not (game_dir / entry_name).is_file():
            raise ConfigError(f"games[{index}]: entry file not found: {game_dir / entry_name}")

        thumbnail_name = _optional_str(item, "thumbnail", index)
        thumbnail: Path | None = None
        if thumbnail_name:
            candidate = game_dir / thumbnail_name
            if candidate.is_file():
                thumbnail = candidate

        python_value = _optional_str(item, "python", index)
        python: Path | None = None
        if python_value:
            python = hub_root / python_value

        games.append(
            GameEntry(
                id=game_id,
                title=title,
                description=description,
                dir=game_dir,
                entry=entry_name,
                thumbnail=thumbnail,
                python=python,
            )
        )

    return games


def load_games(path: Path, hub_root: Path) -> list[GameEntry]:
    """Read games.json from disk and return validated game entries."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read {path}: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc

    return parse_games(data, hub_root)
