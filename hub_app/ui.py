"""Pygame drawing for the hub screen.

Surfaces are never converted with convert(), so they survive a display
re-init when a game is launched and the hub window is recreated.
"""

import math
from pathlib import Path

import numpy as np
import pygame

from hub_app.config import GameEntry

BACKGROUND = (18, 20, 28)
TEXT = (235, 235, 240)
MUTED = (150, 155, 170)
HIGHLIGHT = (80, 200, 255)
CARD_BG = (34, 38, 52)
ERROR_BG = (170, 30, 30)
PLACEHOLDER_COLORS = [
    (96, 125, 216),
    (216, 110, 96),
    (96, 183, 128),
    (206, 170, 84),
    (160, 110, 200),
]

PREVIEW_SIZE = (240, 180)
THUMB_SIZE = (240, 180)
HELP_WITH_HAND = "Move your hand left/right to choose. Pinch and hold to play."
HELP_NO_HAND = "Show your hand to the camera"


def make_fonts() -> dict[str, pygame.font.Font]:
    return {
        "title": pygame.font.Font(None, 72),
        "name": pygame.font.Font(None, 44),
        "body": pygame.font.Font(None, 32),
        "small": pygame.font.Font(None, 26),
    }


def load_thumbnail(path: Path | None, size: tuple[int, int]) -> pygame.Surface | None:
    if path is None:
        return None
    try:
        image = pygame.image.load(str(path))
        return pygame.transform.smoothscale(image, size)
    except (pygame.error, OSError, ValueError):
        return None


def _placeholder_color(game_id: str) -> tuple[int, int, int]:
    return PLACEHOLDER_COLORS[sum(map(ord, game_id)) % len(PLACEHOLDER_COLORS)]


def _draw_card(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    game: GameEntry,
    thumb: pygame.Surface | None,
    rect: pygame.Rect,
    highlighted: bool,
) -> None:
    pygame.draw.rect(screen, CARD_BG, rect, border_radius=12)

    inner = rect.inflate(-16, -16)
    if thumb is not None:
        if thumb.get_size() != inner.size:
            thumb = pygame.transform.smoothscale(thumb, inner.size)
        screen.blit(thumb, inner.topleft)
    else:
        pygame.draw.rect(screen, _placeholder_color(game.id), inner, border_radius=8)
        letter = fonts["title"].render(game.title[:1].upper(), True, TEXT)
        screen.blit(letter, letter.get_rect(center=inner.center))

    if highlighted:
        pygame.draw.rect(screen, HIGHLIGHT, rect, width=4, border_radius=12)


def _draw_hold_arc(
    screen: pygame.Surface, rect: pygame.Rect, hold_progress: float
) -> None:
    if hold_progress <= 0.0:
        return
    radius = max(rect.width, rect.height) // 2 + 18
    arc_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    arc_rect.center = rect.center
    start = math.pi / 2
    end = start + 2 * math.pi * min(1.0, hold_progress)
    pygame.draw.arc(screen, HIGHLIGHT, arc_rect, start, end, 6)


def _draw_preview(screen: pygame.Surface, preview_rgb: np.ndarray) -> None:
    surface = pygame.surfarray.make_surface(preview_rgb.swapaxes(0, 1))
    surface = pygame.transform.smoothscale(surface, PREVIEW_SIZE)
    margin = 20
    x = screen.get_width() - PREVIEW_SIZE[0] - margin
    y = screen.get_height() - PREVIEW_SIZE[1] - margin
    screen.blit(surface, (x, y))
    pygame.draw.rect(screen, MUTED, (x, y, *PREVIEW_SIZE), width=2)


def draw_hub(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    games: list[GameEntry],
    thumbs: list[pygame.Surface | None],
    selected: int,
    hold_progress: float,
    hand_visible: bool,
    preview_rgb: np.ndarray | None,
    error_text: str | None,
) -> None:
    width, height = screen.get_size()
    screen.fill(BACKGROUND)

    title = fonts["title"].render("Choose a game", True, TEXT)
    screen.blit(title, title.get_rect(center=(width // 2, height * 0.12)))

    count = len(games)
    slot = width / (count + 1)
    base_w = int(min(slot * 0.8, 320))
    base_h = int(base_w * 0.75)
    center_y = int(height * 0.45)

    for index, game in enumerate(games):
        is_selected = index == selected
        scale = 1.2 if is_selected else 1.0
        w, h = int(base_w * scale), int(base_h * scale)
        center_x = int(slot * (index + 1))
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (center_x, center_y)
        thumb = thumbs[index] if index < len(thumbs) else None
        _draw_card(screen, fonts, game, thumb, rect, is_selected)
        if is_selected:
            _draw_hold_arc(screen, rect, hold_progress)

    if games:
        selected_game = games[selected]
        name = fonts["name"].render(selected_game.title, True, TEXT)
        screen.blit(name, name.get_rect(center=(width // 2, int(height * 0.78))))
        if selected_game.description:
            desc = fonts["body"].render(selected_game.description, True, MUTED)
            screen.blit(desc, desc.get_rect(center=(width // 2, int(height * 0.84))))

    help_text = HELP_WITH_HAND if hand_visible else HELP_NO_HAND
    help_surface = fonts["small"].render(help_text, True, MUTED)
    screen.blit(help_surface, help_surface.get_rect(center=(width // 2, int(height * 0.93))))

    if preview_rgb is not None:
        _draw_preview(screen, preview_rgb)

    if error_text:
        banner = fonts["body"].render(error_text, True, TEXT)
        padding = 12
        banner_rect = banner.get_rect(center=(width // 2, int(height * 0.04)))
        background = banner_rect.inflate(padding * 2, padding)
        pygame.draw.rect(screen, ERROR_BG, background, border_radius=8)
        screen.blit(banner, banner_rect)


def draw_message(
    screen: pygame.Surface, fonts: dict[str, pygame.font.Font], text: str
) -> None:
    screen.fill(BACKGROUND)
    surface = fonts["name"].render(text, True, TEXT)
    screen.blit(surface, surface.get_rect(center=screen.get_rect().center))
