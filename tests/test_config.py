import json
from pathlib import Path

import pytest

from hub_app.config import ConfigError, GameEntry, load_games, parse_games


def make_game_dir(root: Path, name: str = "alpha", entry: str = "main.py") -> Path:
    game_dir = root / "games" / name
    game_dir.mkdir(parents=True)
    (game_dir / entry).write_text("print('hi')\n", encoding="utf-8")
    return game_dir


def valid_entry(**overrides):
    entry = {
        "id": "alpha",
        "title": "Alpha",
        "description": "Play alpha",
        "dir": "games/alpha",
        "entry": "main.py",
        "thumbnail": None,
    }
    entry.update(overrides)
    return entry


def test_valid_entry_resolves_absolute_paths(tmp_path):
    make_game_dir(tmp_path)
    thumb = tmp_path / "games" / "alpha" / "thumb.png"
    thumb.write_bytes(b"png")
    data = {"games": [valid_entry(thumbnail="thumb.png")]}

    games = parse_games(data, tmp_path)

    assert len(games) == 1
    game = games[0]
    assert isinstance(game, GameEntry)
    assert game.id == "alpha"
    assert game.title == "Alpha"
    assert game.description == "Play alpha"
    assert game.dir.is_absolute()
    assert game.dir == (tmp_path / "games" / "alpha").resolve()
    assert game.entry == "main.py"
    assert game.thumbnail == game.dir / "thumb.png"
    assert game.python is None


def test_missing_games_key_raises(tmp_path):
    with pytest.raises(ConfigError):
        parse_games({}, tmp_path)


def test_empty_games_list_raises(tmp_path):
    with pytest.raises(ConfigError):
        parse_games({"games": []}, tmp_path)


def test_duplicate_ids_raise(tmp_path):
    make_game_dir(tmp_path, "alpha")
    make_game_dir(tmp_path, "beta")
    data = {
        "games": [
            valid_entry(),
            valid_entry(dir="games/beta"),
        ]
    }

    with pytest.raises(ConfigError):
        parse_games(data, tmp_path)


def test_missing_entry_file_raises(tmp_path):
    make_game_dir(tmp_path)
    data = {"games": [valid_entry(entry="missing.py")]}

    with pytest.raises(ConfigError):
        parse_games(data, tmp_path)


def test_missing_game_dir_raises(tmp_path):
    data = {"games": [valid_entry(dir="games/nope")]}

    with pytest.raises(ConfigError):
        parse_games(data, tmp_path)


def test_missing_required_string_raises(tmp_path):
    make_game_dir(tmp_path)
    entry = valid_entry()
    del entry["title"]

    with pytest.raises(ConfigError):
        parse_games({"games": [entry]}, tmp_path)


def test_description_defaults_to_empty_string(tmp_path):
    make_game_dir(tmp_path)
    entry = valid_entry()
    del entry["description"]

    games = parse_games({"games": [entry]}, tmp_path)

    assert games[0].description == ""


def test_missing_thumbnail_file_becomes_none(tmp_path):
    make_game_dir(tmp_path)
    data = {"games": [valid_entry(thumbnail="does-not-exist.png")]}

    games = parse_games(data, tmp_path)

    assert games[0].thumbnail is None


def test_optional_python_is_resolved_relative_to_hub_root(tmp_path):
    make_game_dir(tmp_path)
    data = {"games": [valid_entry(python=".venv/bin/python")]}

    games = parse_games(data, tmp_path)

    assert games[0].python == tmp_path / ".venv" / "bin" / "python"


def test_load_games_reads_json_file(tmp_path):
    make_game_dir(tmp_path)
    config_path = tmp_path / "games.json"
    config_path.write_text(json.dumps({"games": [valid_entry()]}), encoding="utf-8")

    games = load_games(config_path, tmp_path)

    assert [g.id for g in games] == ["alpha"]


def test_load_games_invalid_json_raises(tmp_path):
    config_path = tmp_path / "games.json"
    config_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_games(config_path, tmp_path)
