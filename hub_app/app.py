"""Hub main loop: pick a game with the hand or keyboard, then launch it."""

import os
import sys
import time
from pathlib import Path

import pygame

from hub_app.config import ConfigError, GameEntry, load_games
from hub_app.gestures import MIDDLE_MCP, HoldConfirm, PinchDetector, pinch_ratio
from hub_app.launcher import run_game
from hub_app.selection import SelectionTracker
from hub_app.tracker import HandFrame, HandTracker
from hub_app.ui import THUMB_SIZE, draw_hub, draw_message, load_thumbnail, make_fonts

RETURN_COOLDOWN_S = 2.0
ERROR_DISPLAY_S = 5.0
FPS = 30
CAMERA_ATTEMPTS = 3
CAMERA_RETRY_DELAY_S = 0.5
GAME_EXIT_PAUSE_S = 0.5
WINDOW_SIZE = (1280, 720)
MODEL_MISSING_TEXT = "Hand model missing: models/hand_landmarker.task"
CAMERA_UNAVAILABLE_TEXT = "Camera not available - use keyboard"


def open_display() -> pygame.Surface:
    if os.environ.get("HUB_WINDOWED") == "1":
        screen = pygame.display.set_mode(WINDOW_SIZE)
    else:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Game Hub")
    return screen


def camera_index_from_env() -> int:
    try:
        return int(os.environ.get("HUB_CAMERA_INDEX", "0"))
    except ValueError:
        return 0


def open_tracker(tracker: HandTracker, model_path: Path) -> str | None:
    """Return None when the camera is ready, otherwise the banner text."""
    if not model_path.is_file():
        return MODEL_MISSING_TEXT
    return None if tracker.open() else CAMERA_UNAVAILABLE_TEXT


def launch_game(
    game: GameEntry,
    tracker: HandTracker,
    model_path: Path,
    fonts: dict,
) -> str | None:
    """Run a game in a child process and restore the hub. Returns a banner or None."""
    draw_message(pygame.display.get_surface(), fonts, f"Starting {game.title}...")
    pygame.display.flip()
    tracker.close()
    time.sleep(GAME_EXIT_PAUSE_S)

    pygame.display.quit()
    result = run_game(game, sys.executable)

    pygame.display.init()
    open_display()
    pygame.event.clear()
    pygame.mouse.set_visible(False)
    draw_message(pygame.display.get_surface(), fonts, "Loading camera...")
    pygame.display.flip()

    camera_error = None
    for attempt in range(CAMERA_ATTEMPTS):
        camera_error = open_tracker(tracker, model_path)
        if camera_error is None:
            break
        if attempt < CAMERA_ATTEMPTS - 1:
            time.sleep(CAMERA_RETRY_DELAY_S)

    if not result.ok:
        return f"{game.title} failed: {result.message}"
    return camera_error


def main() -> int:
    hub_root = Path(__file__).resolve().parent.parent
    model_path = hub_root / "models" / "hand_landmarker.task"

    try:
        games = load_games(hub_root / "games.json", hub_root)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    pygame.init()
    open_display()
    fonts = make_fonts()
    thumbs = [load_thumbnail(g.thumbnail, THUMB_SIZE) for g in games]

    tracker = HandTracker(model_path, camera_index_from_env())
    error_text = open_tracker(tracker, model_path)
    error_until = time.monotonic() + ERROR_DISPLAY_S if error_text else 0.0

    selection = SelectionTracker(len(games))
    pinch = PinchDetector()
    hold = HoldConfirm()
    cooldown_until = 0.0
    hand = HandFrame(None, None)
    clock = pygame.time.Clock()
    running = True

    while running:
        now = time.monotonic()
        keyboard_launch = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    selection.step(-1)
                elif event.key == pygame.K_RIGHT:
                    selection.step(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    keyboard_launch = True
                elif event.key == pygame.K_F5:
                    error_text = open_tracker(tracker, model_path)
                    error_until = now + ERROR_DISPLAY_S if error_text else 0.0

        if not running:
            break

        hand = tracker.read()
        landmarks = hand.landmarks
        gesture_fired = False
        hold_progress = 0.0

        if now >= cooldown_until:
            pinched = pinch.update(pinch_ratio(landmarks) if landmarks else None)
            if not pinched:
                selection.update_from_x(landmarks[MIDDLE_MCP][0] if landmarks else None)
            gesture_fired = hold.update(pinched, now)
            hold_progress = hold.progress(now)
        else:
            pinch.update(None)
            hold.reset()

        if gesture_fired or keyboard_launch:
            error_text = launch_game(games[selection.index], tracker, model_path, fonts)
            error_until = time.monotonic() + ERROR_DISPLAY_S if error_text else 0.0
            cooldown_until = time.monotonic() + RETURN_COOLDOWN_S
            pinch.update(None)
            hold.reset()
            hand = HandFrame(None, None)
            pygame.event.clear()
            continue

        if error_text and now >= error_until:
            error_text = None

        screen = pygame.display.get_surface()
        draw_hub(
            screen,
            fonts,
            games,
            thumbs,
            selection.index,
            hold_progress,
            landmarks is not None,
            hand.rgb,
            error_text,
        )
        pygame.display.flip()
        clock.tick(FPS)

    tracker.close()
    pygame.quit()
    return 0
