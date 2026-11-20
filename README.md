# Game Hub

A gesture-controlled launcher. It shows the games listed in `games.json` on a
hub screen. Move your hand left or right to choose a game, then pinch and hold
to start it. When the game exits you return to the hub.

Both games and the hub share one Python virtual environment (`.venv`).

## About

This is a project for fairs and exhibitions. It was built by Computer
Engineering students at Instituto Profesional Santo Tomás, Chillán, Chile.

| Game | Folder | Original repository |
|------|--------|---------------------|
| Space Invaders: Hand Control Edition | `games/space-invaders` | [Reas0nt/SpaceInvaderHandControl](https://github.com/Reas0nt/SpaceInvaderHandControl) |
| Flappy Hand | `games/flappy` | [Maikol2305/Flappy-Bird](https://github.com/Maikol2305/Flappy-Bird) |

The games are copied into this repository. Space Invaders was migrated from the
legacy `mp.solutions` API to the MediaPipe Tasks API so both games share
`mediapipe==1.2.3`.

## Requirements

- Python 3.12
- A webcam
- `models/hand_landmarker.task` (included in the repository)

## Setup

### Linux

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
chmod +x run.sh
./run.sh
```

### Windows

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
run.bat
```

## Controls

| Action | Gesture | Keyboard |
| --- | --- | --- |
| Move selection | Move your hand left/right | Left / Right arrows |
| Start selected game | Pinch and hold (about 0.8 s) | Enter or Space |
| Retry camera | - | F5 |
| Quit the hub | - | Esc |

After a game exits, gestures are ignored for 2 seconds so a pinch from the
game does not start another one.

## Environment variables

- `HUB_CAMERA_INDEX`: camera index to open (default `0`).
- `HUB_WINDOWED=1`: run in a 1280x720 window instead of fullscreen.

## Adding a game

Add an object to the `games` list in `games.json`:

```json
{
  "id": "my-game",
  "title": "My Game",
  "description": "Short hint shown under the card.",
  "dir": "games/my-game",
  "entry": "main.py",
  "thumbnail": "thumb.png",
  "python": null
}
```

- `dir` is relative to the hub folder. `entry` is relative to `dir`.
- `thumbnail` is relative to the game folder. Use `null` or omit it for a
  colored placeholder.
- `python` is optional. Relative paths are resolved from the hub folder.
  When omitted, the game runs with the hub's Python (`.venv`).
- `id` must be unique.

## Running the tests

```sh
.venv/bin/python -m pytest -q
```

On Windows use `.venv\Scripts\python -m pytest -q`.

## Troubleshooting

- **"Camera not available - use keyboard"**: another application may be using
  the webcam. Close it, then press F5. Or set `HUB_CAMERA_INDEX` to another
  camera.
- **"Hand model missing"**: `models/hand_landmarker.task` is not present.
  Restore it from the repository.
- **`module 'mediapipe' has no attribute 'solutions'`**: old game code. All code
  uses the MediaPipe Tasks API (`mediapipe==1.2.3`). Update the file and
  reinstall with `requirements.txt`.
- **A game fails right after starting**: the failure message on the hub shows
  the last line of the game's error output.
