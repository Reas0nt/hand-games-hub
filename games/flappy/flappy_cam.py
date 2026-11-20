import cv2
import pygame
import random
import sys
import os
import math
import numpy as np
import json
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ---------------------------------------------------------
# 1. Configuración de Pygame y Pantalla
# ---------------------------------------------------------
pygame.init()
WIDTH, HEIGHT = 420, 640  # Resolución lógica interna del juego

# Configuración inicial: ARRANCA DIRECTAMENTE EN PANTALLA COMPLETA
fullscreen = True
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Flappy Bird - Control por Mano (MediaPipe)")
clock = pygame.time.Clock()

# Paleta de Colores
SKY_TOP = (55, 160, 235)
SKY_BOTTOM = (175, 225, 255)
GROUND_COLOR = (222, 212, 140)
GROUND_BORDER = (105, 185, 45)
PIPE_GREEN = (95, 195, 45)
PIPE_DARK = (60, 140, 30)
PIPE_LIGHT = (145, 225, 80)
PIPE_BORDER = (25, 75, 15)

YELLOW_BIRD = (255, 215, 0)
ORANGE_BEAK = (255, 95, 20)
CHE_PINK = (255, 140, 140)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (235, 60, 60)
GOLD = (255, 215, 0)
DARK_OVERLAY = (0, 0, 0, 140)

# Fuentes
font_small = pygame.font.SysFont("Segoe UI", 15, bold=True)
font_mid = pygame.font.SysFont("Segoe UI", 21, bold=True)
font_score = pygame.font.SysFont("Segoe UI", 36, bold=True)
font_title = pygame.font.SysFont("Segoe UI", 38, bold=True)

# ---------------------------------------------------------
# 2. Configuración de Niveles y Modos del Juego
# ---------------------------------------------------------
CAMPAIGN_LEVELS = [
    {
        "id": 1,
        "name": "NIVEL 1: VALLE VERDE",
        "subtitle": "¡Controla el vuelo con tu mano!",
        "target_pipes": 8,
        "speed": 5.0,
        "gap": 175,
        "moving_prob": 0.0,
        "sky_top": (55, 160, 235),
        "sky_bottom": (175, 225, 255),
        "pipe_colors": ((95, 195, 45), (60, 140, 30), (145, 225, 80), (25, 75, 15)),
        "night": False,
        "infinite": False
    },
    {
        "id": 2,
        "name": "NIVEL 2: ATARDECER DORADO",
        "subtitle": "Mayor velocidad y tubos móviles",
        "target_pipes": 12,
        "speed": 6.5,
        "gap": 165,
        "moving_prob": 0.45,
        "sky_top": (235, 95, 60),
        "sky_bottom": (255, 195, 115),
        "pipe_colors": ((210, 110, 35), (145, 70, 20), (245, 160, 75), (90, 40, 10)),
        "night": False,
        "infinite": False
    },
    {
        "id": 3,
        "name": "NIVEL 3: NOCHE MÍSTICA",
        "subtitle": "¡Desafío final bajo las estrellas!",
        "target_pipes": 16,
        "speed": 8.0,
        "gap": 155,
        "moving_prob": 0.70,
        "sky_top": (18, 18, 48),
        "sky_bottom": (65, 40, 95),
        "pipe_colors": ((45, 175, 195), (25, 110, 125), (105, 225, 240), (15, 60, 70)),
        "night": True,
        "infinite": False
    }
]

INFINITE_LEVEL = {
    "id": "∞",
    "name": "MODO INFINITO",
    "subtitle": "¡Aumento de velocidad cada 5 tuberías!",
    "target_pipes": 999999,
    "speed": 5.5,
    "gap": 170,
    "moving_prob": 0.60,
    "sky_top": (40, 10, 50),
    "sky_bottom": (120, 20, 80),
    "pipe_colors": ((200, 50, 80), (130, 20, 50), (240, 100, 130), (80, 10, 30)),
    "night": True,
    "infinite": True
}

# ---------------------------------------------------------
# 3. Sintetizador de Sonidos Retro (NumPy + Pygame Mixer)
# ---------------------------------------------------------
sounds_enabled = False
sound_flap = None
sound_score = None
sound_hit = None
sound_record = None
sound_coin = None
sound_win = None

try:
    pygame.mixer.init(22050, -16, 2, 512)
    sr = 22050

    def generate_sound(wave_mono):
        mono = (wave_mono * 14000).astype(np.int16)
        stereo = np.column_stack((mono, mono))
        return pygame.sndarray.make_sound(stereo)

    # Sonido de aleteo / ascenso
    n_flap = int(sr * 0.08)
    t_f = np.linspace(0, 0.08, n_flap, False)
    freqs_f = np.linspace(340, 620, n_flap)
    w_f = np.sin(2 * np.pi * np.cumsum(freqs_f) / sr) * np.exp(-3.5 * t_f / 0.08)
    sound_flap = generate_sound(w_f)

    # Sonido de puntuación
    n1, n2 = int(sr * 0.06), int(sr * 0.12)
    t1, t2 = np.linspace(0, 0.06, n1, False), np.linspace(0, 0.12, n2, False)
    w1 = np.sin(2 * np.pi * 659 * t1) * 0.85
    w2 = np.sin(2 * np.pi * 987 * t2) * np.exp(-2.5 * t2 / 0.12)
    sound_score = generate_sound(np.concatenate([w1, w2]))

    # Sonido de colisión / impacto
    n_h = int(sr * 0.28)
    t_h = np.linspace(0, 0.28, n_h, False)
    noise = np.random.uniform(-0.45, 0.45, n_h)
    freqs_h = np.linspace(220, 50, n_h)
    w_h = (np.sin(2 * np.pi * np.cumsum(freqs_h) / sr) * 0.55 + noise) * np.exp(-3.8 * t_h / 0.28)
    sound_hit = generate_sound(w_h)

    # Sonido de récord batido
    n_note = int(sr * 0.08)
    t_n = np.linspace(0, 0.08, n_note, False)
    c5 = np.sin(2 * np.pi * 523 * t_n)
    e5 = np.sin(2 * np.pi * 659 * t_n)
    g5 = np.sin(2 * np.pi * 784 * t_n) * np.exp(-1.5 * t_n / 0.08)
    sound_record = generate_sound(np.concatenate([c5, e5, g5]))

    # Sonido de moneda coleccionable
    n_c1, n_c2 = int(sr * 0.05), int(sr * 0.10)
    t_c1, t_c2 = np.linspace(0, 0.05, n_c1, False), np.linspace(0, 0.10, n_c2, False)
    wc1 = np.sin(2 * np.pi * 987 * t_c1) * 0.8
    wc2 = np.sin(2 * np.pi * 1318 * t_c2) * np.exp(-3.0 * t_c2 / 0.10)
    sound_coin = generate_sound(np.concatenate([wc1, wc2]))

    # Sonido de nivel superado / victoria
    n_w = int(sr * 0.08)
    t_w = np.linspace(0, 0.08, n_w, False)
    w_c5 = np.sin(2 * np.pi * 523 * t_w)
    w_e5 = np.sin(2 * np.pi * 659 * t_w)
    w_g5 = np.sin(2 * np.pi * 784 * t_w)
    w_c6 = np.sin(2 * np.pi * 1046 * t_w) * np.exp(-1.0 * t_w / 0.08)
    sound_win = generate_sound(np.concatenate([w_c5, w_e5, w_g5, w_c6]))

    sounds_enabled = True
except Exception as e:
    print(f"Aviso de audio: no se pudo inicializar sonido sintetizado ({e})")

def play_sfx(sfx):
    if sounds_enabled and sfx:
        try:
            sfx.play()
        except Exception:
            pass

# ---------------------------------------------------------
# 4. Detector de Manos (MediaPipe HandLandmarker)
# ---------------------------------------------------------
hand_model_filename = "hand_landmarker.task"
if not os.path.exists(hand_model_filename):
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    print("Descargando modelo de detección de manos (MediaPipe)...")
    urllib.request.urlretrieve(url, hand_model_filename)

base_options = python.BaseOptions(model_asset_path=hand_model_filename)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1
)
hand_detector = vision.HandLandmarker.create_from_options(options)

# Conexiones anatómicas de los 21 puntos de la mano
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Pulgar
    (0, 5), (5, 6), (6, 7), (7, 8),         # Índice
    (5, 9), (9, 10), (10, 11), (11, 12),    # Medio
    (9, 13), (13, 14), (14, 15), (15, 16),  # Anular
    (13, 17), (17, 18), (18, 19), (19, 20), # Meñique
    (0, 17)                                 # Base de la palma
]

# ---------------------------------------------------------
# Configuración de Selección de Cámara
# ---------------------------------------------------------
CAMERA_INDEX = 1  # 0 = Cámara integrada del notebook, 1 o 2 = Cámara USB / externa

cap = cv2.VideoCapture(CAMERA_INDEX)

# Verificación de respaldo (fallback a cámara 0 si la externa no está conectada)
if not cap.isOpened() and CAMERA_INDEX != 0:
    print(f"No se pudo abrir la cámara {CAMERA_INDEX}. Intentando con la cámara predeterminada (0)...")
    cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# Récord Máximo Persistente
HIGHSCORE_FILE = "highscore.txt"
def get_high_score():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def save_high_score(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(score))
    except Exception:
        pass

# Registro de Iniciales de Ganadores
WINNERS_FILE = "ganadores.txt"

def save_winner_initials(initials, score):
    clean_initials = initials.strip().upper()[:3]
    if not clean_initials:
        clean_initials = "AAA"
    try:
        with open(WINNERS_FILE, "a", encoding="utf-8") as f:
            f.write(f"Iniciales: {clean_initials} | Puntos: {score}\n")
    except Exception:
        pass

# ---------------------------------------------------------
# 5. Clases del Juego y Efectos Visuales
# ---------------------------------------------------------
class Particle:
    """Partículas de estela y plumas."""
    def __init__(self, x, y, vx, vy, color, size, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.age = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08
        self.age += 1
        return self.age < self.lifetime

    def draw(self, surface):
        alpha_ratio = 1.0 - (self.age / self.lifetime)
        current_size = max(1, int(self.size * alpha_ratio))
        surf = pygame.Surface((current_size * 2, current_size * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color[:3], int(220 * alpha_ratio))
        pygame.draw.circle(surf, color_with_alpha, (current_size, current_size), current_size)
        surface.blit(surf, (int(self.x - current_size), int(self.y - current_size)))

class Confetti:
    """Partículas de confeti festivo para celebración."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-4.5, 4.5)
        self.vy = random.uniform(-7.0, -1.5)
        self.color = random.choice([
            (255, 70, 70), (70, 255, 130), (70, 180, 255),
            (255, 225, 50), (255, 110, 200), (190, 80, 255)
        ])
        self.w = random.randint(6, 12)
        self.h = random.randint(4, 8)
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-9, 9)
        self.age = 0
        self.lifetime = random.randint(55, 95)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.16
        self.angle += self.rot_speed
        self.age += 1
        return self.age < self.lifetime

    def draw(self, surface):
        if self.age >= self.lifetime:
            return
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        surf.fill(self.color)
        rot_surf = pygame.transform.rotate(surf, self.angle)
        surface.blit(rot_surf, (int(self.x), int(self.y)))

class FloatingText:
    """Texto flotante emergente (+1, +2)."""
    def __init__(self, x, y, text, color=(255, 230, 80)):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.age = 0
        self.lifetime = 35

    def update(self):
        self.y -= 1.4
        self.age += 1
        return self.age < self.lifetime

    def draw(self, surface):
        alpha = int(255 * (1.0 - self.age / self.lifetime))
        txt = font_mid.render(self.text, True, self.color)
        txt.set_alpha(alpha)
        surface.blit(txt, (int(self.x - txt.get_width() // 2), int(self.y)))

class Coin:
    """Moneda de bonificación coleccionable interactiva."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 12
        self.timer = random.uniform(0, math.pi * 2)
        self.collected = False

    def update(self, speed):
        self.x -= speed
        self.timer += 0.12

    def draw(self, surface):
        if self.collected:
            return
        scale_x = max(0.2, abs(math.cos(self.timer)))
        w = int(self.radius * 2 * scale_x)
        h = self.radius * 2
        coin_surf = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        cx, cy = (w + 4) // 2, (h + 4) // 2

        pygame.draw.ellipse(coin_surf, (190, 140, 20), (cx - w // 2, cy - h // 2, w, h))
        pygame.draw.ellipse(coin_surf, GOLD, (cx - w // 2 + 1, cy - h // 2 + 1, max(1, w - 2), max(1, h - 2)))
        if w > 8:
            pygame.draw.ellipse(coin_surf, (255, 245, 180), (cx - w // 4, cy - h // 4, max(1, w // 2), max(1, h // 2)))
        surface.blit(coin_surf, (int(self.x - cx), int(self.y - cy)))

    def collide(self, bird):
        if self.collected:
            return False
        dist_sq = (self.x - bird.x) ** 2 + (self.y - bird.y) ** 2
        return dist_sq < (self.radius + bird.radius) ** 2

class Cloud:
    """Nubes procedimentales con efecto de paralaje."""
    def __init__(self, x, layer=1):
        self.layer = layer
        self.x = x
        self.y = random.randint(40, 240)
        self.speed = 0.5 if layer == 1 else 1.1
        self.scale = random.uniform(0.7, 1.1) if layer == 1 else random.uniform(1.1, 1.6)
        self.alpha = 110 if layer == 1 else 170

    def update(self):
        self.x -= self.speed
        if self.x < -140:
            self.x = WIDTH + random.randint(20, 90)
            self.y = random.randint(40, 240)

    def draw(self, surface):
        cloud_surf = pygame.Surface((int(100 * self.scale), int(50 * self.scale)), pygame.SRCALPHA)
        color = (255, 255, 255, self.alpha)
        s = self.scale
        pygame.draw.circle(cloud_surf, color, (int(25 * s), int(30 * s)), int(18 * s))
        pygame.draw.circle(cloud_surf, color, (int(50 * s), int(20 * s)), int(24 * s))
        pygame.draw.circle(cloud_surf, color, (int(75 * s), int(30 * s)), int(18 * s))
        pygame.draw.ellipse(cloud_surf, color, (int(10 * s), int(22 * s), int(80 * s), int(24 * s)))
        surface.blit(cloud_surf, (int(self.x), int(self.y)))

class Bird:
    """Pájaro animado con rotación dinámica y aleteo expresivo."""
    def __init__(self):
        self.x = 90
        self.y = HEIGHT // 2
        self.prev_y = self.y
        self.radius = 20
        self.target_y = HEIGHT // 2
        self.angle = 0
        self.wing_timer = 0
        self.flap_cooldown = 0

    def update(self, detected_y_ratio):
        self.prev_y = self.y

        if detected_y_ratio is not None:
            min_cam_y, max_cam_y = 0.15, 0.80
            norm_y = (detected_y_ratio - min_cam_y) / (max_cam_y - min_cam_y)
            norm_y = max(0.0, min(1.0, norm_y))
            self.target_y = int(norm_y * (HEIGHT - 170) + 60)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.target_y = max(60, self.target_y - 9)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.target_y = min(HEIGHT - 110, self.target_y + 9)

        vy = (self.target_y - self.y) * 0.22
        self.y += vy

        if vy < -2.8 and self.flap_cooldown <= 0:
            play_sfx(sound_flap)
            self.flap_cooldown = 14
        if self.flap_cooldown > 0:
            self.flap_cooldown -= 1

        target_angle = -vy * 4.5
        target_angle = max(-35.0, min(55.0, target_angle))
        self.angle += (target_angle - self.angle) * 0.2
        self.wing_timer += 0.25 if vy >= 0 else 0.45

    def draw(self, surface):
        size = self.radius * 3
        bird_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        pygame.draw.circle(bird_surf, (220, 175, 10), (cx, cy + 2), self.radius)
        pygame.draw.circle(bird_surf, YELLOW_BIRD, (cx, cy), self.radius)
        pygame.draw.circle(bird_surf, (255, 238, 115), (cx - 4, cy - 5), self.radius - 6)
        pygame.draw.circle(bird_surf, CHE_PINK, (cx + 3, cy + 8), 5)

        pygame.draw.circle(bird_surf, WHITE, (cx + 8, cy - 6), 6)
        pygame.draw.circle(bird_surf, BLACK, (cx + 10, cy - 6), 3)
        pygame.draw.circle(bird_surf, WHITE, (cx + 11, cy - 8), 1)

        pygame.draw.polygon(bird_surf, ORANGE_BEAK, [
            (cx + 13, cy - 2),
            (cx + 25, cy + 4),
            (cx + 13, cy + 9)
        ])
        pygame.draw.line(bird_surf, (190, 60, 10), (cx + 13, cy + 4), (cx + 24, cy + 4), 1)

        wing_offset_y = int(math.sin(self.wing_timer) * 6)
        wing_rect = pygame.Rect(cx - 15, cy - 4 + wing_offset_y, 16, 11)
        pygame.draw.ellipse(bird_surf, (245, 185, 15), wing_rect)
        pygame.draw.ellipse(bird_surf, WHITE, wing_rect, 1)

        pygame.draw.circle(bird_surf, (180, 140, 20), (cx, cy), self.radius, 2)

        rotated_surf = pygame.transform.rotate(bird_surf, self.angle)
        rect = rotated_surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_surf, rect)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius + 3, self.y - self.radius + 3, (self.radius - 3) * 2, (self.radius - 3) * 2)

class Pipe:
    """Tubo con gráficos 3D retro, sombras y oscilación opcional."""
    def __init__(self, x, current_speed, gap=165, is_moving=False, colors=None):
        self.x = x
        self.gap = gap
        self.base_top_height = random.randint(70, HEIGHT - 120 - self.gap - 80)
        self.top_height = self.base_top_height
        self.bottom_y = self.top_height + self.gap
        self.width = 66
        self.speed = current_speed
        self.passed = False
        self.is_moving = is_moving
        self.osc_angle = random.uniform(0, math.pi * 2)
        self.osc_speed = random.uniform(0.04, 0.07)
        if colors is None:
            self.color = PIPE_GREEN
            self.dark = PIPE_DARK
            self.light = PIPE_LIGHT
            self.border = PIPE_BORDER
        else:
            self.color, self.dark, self.light, self.border = colors

    def update(self):
        self.x -= self.speed
        if self.is_moving:
            self.osc_angle += self.osc_speed
            offset = math.sin(self.osc_angle) * 32
            self.top_height = max(50, min(HEIGHT - 210, int(self.base_top_height + offset)))
            self.bottom_y = self.top_height + self.gap

    def draw(self, surface):
        lip_height = 24
        lip_overhang = 5

        body_rect_top = pygame.Rect(self.x, 0, self.width, self.top_height - lip_height)
        self._draw_pipe_segment(surface, body_rect_top)
        lip_rect_top = pygame.Rect(self.x - lip_overhang, self.top_height - lip_height, self.width + lip_overhang * 2, lip_height)
        self._draw_pipe_segment(surface, lip_rect_top, is_lip=True)

        lip_rect_bot = pygame.Rect(self.x - lip_overhang, self.bottom_y, self.width + lip_overhang * 2, lip_height)
        self._draw_pipe_segment(surface, lip_rect_bot, is_lip=True)
        body_rect_bot = pygame.Rect(self.x, self.bottom_y + lip_height, self.width, HEIGHT - (self.bottom_y + lip_height))
        self._draw_pipe_segment(surface, body_rect_bot)

    def _draw_pipe_segment(self, surface, rect, is_lip=False):
        if rect.height <= 0:
            return
        pygame.draw.rect(surface, self.color, rect)
        shadow_w = 12 if is_lip else 10
        shadow_rect = pygame.Rect(rect.right - shadow_w, rect.y, shadow_w, rect.height)
        pygame.draw.rect(surface, self.dark, shadow_rect)
        highlight_rect = pygame.Rect(rect.x + (6 if is_lip else 5), rect.y, 6, rect.height)
        pygame.draw.rect(surface, self.light, highlight_rect)
        pygame.draw.rect(surface, self.border, rect, 2)

    def collide(self, bird):
        bird_rect = bird.get_rect()
        top_rect = pygame.Rect(self.x - 3, 0, self.width + 6, self.top_height)
        bottom_rect = pygame.Rect(self.x - 3, self.bottom_y, self.width + 6, HEIGHT - self.bottom_y)
        return bird_rect.colliderect(top_rect) or bird_rect.colliderect(bottom_rect)

# ---------------------------------------------------------
# 6. Funciones de Dibujo de Entorno e Interfaz
# ---------------------------------------------------------
def draw_background(surface, level):
    sky_top = level.get("sky_top", SKY_TOP)
    sky_bottom = level.get("sky_bottom", SKY_BOTTOM)
    for y in range(HEIGHT - 70):
        ratio = y / (HEIGHT - 70)
        r = int(sky_top[0] * (1 - ratio) + sky_bottom[0] * ratio)
        g = int(sky_top[1] * (1 - ratio) + sky_bottom[1] * ratio)
        b = int(sky_top[2] * (1 - ratio) + sky_bottom[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

def draw_stars(surface, stars, timer):
    for sx, sy, size in stars:
        twinkle = (math.sin(timer * 2.5 + sx) + 1) * 0.5
        color = (int(180 + 75 * twinkle), int(190 + 65 * twinkle), 255)
        pygame.draw.circle(surface, color, (sx, sy), int(size))

def draw_ground(surface, ground_offset, is_night=False):
    ground_y = HEIGHT - 70
    g_col = (180, 170, 110) if is_night else GROUND_COLOR
    b_col = (70, 140, 60) if is_night else GROUND_BORDER
    pygame.draw.rect(surface, g_col, (0, ground_y, WIDTH, 70))
    pygame.draw.rect(surface, b_col, (0, ground_y, WIDTH, 14))
    pygame.draw.line(surface, PIPE_BORDER, (0, ground_y), (WIDTH, ground_y), 2)
    pygame.draw.line(surface, PIPE_BORDER, (0, ground_y + 14), (WIDTH, ground_y + 14), 2)

    stripe_spacing = 24
    offset = int(ground_offset % stripe_spacing)
    stripe_col = (150, 140, 90) if is_night else (198, 185, 115)
    for x in range(-stripe_spacing, WIDTH + stripe_spacing, stripe_spacing):
        sx = x - offset
        pygame.draw.line(surface, stripe_col, (sx, ground_y + 16), (sx - 10, HEIGHT), 3)

def draw_hud(surface, level, pipes_cleared, score, high_score):
    score_shadow = font_score.render(str(score), True, (20, 30, 40))
    score_text = font_score.render(str(score), True, WHITE)
    surface.blit(score_shadow, (18, 14))
    surface.blit(score_text, (16, 12))

    bar_w, bar_h = 160, 15
    bar_x = WIDTH // 2 - bar_w // 2 - 20
    bar_y = 15

    pygame.draw.rect(surface, (20, 30, 40, 210), (bar_x - 3, bar_y - 2, bar_w + 6, bar_h + 4), border_radius=8)
    pygame.draw.rect(surface, (255, 255, 255, 130), (bar_x - 3, bar_y - 2, bar_w + 6, bar_h + 4), 1, border_radius=8)

    if level.get("infinite", False):
        target_str = "∞"
        ratio = (pipes_cleared % 5) / 5.0
    else:
        target = max(1, level["target_pipes"])
        target_str = str(target)
        ratio = min(1.0, pipes_cleared / target)

    fill_w = int(bar_w * ratio)
    if fill_w > 0:
        bar_col = GOLD if level.get("infinite", False) else ((80, 220, 120) if ratio < 1.0 else GOLD)
        pygame.draw.rect(surface, bar_col, (bar_x, bar_y, fill_w, bar_h), border_radius=6)

    lvl_id = level['id']
    lvl_info = f"NIVEL {lvl_id}  {pipes_cleared}/{target_str}" if lvl_id != "∞" else f"MODO ∞  {pipes_cleared} tubos"
    t_info = font_small.render(lvl_info, True, WHITE)
    surface.blit(t_info, (bar_x + bar_w // 2 - t_info.get_width() // 2, bar_y - 1))

    if high_score > 0:
        hs_txt = font_small.render(f"RÉCORD: {high_score}", True, (255, 255, 210))
        surface.blit(hs_txt, (16, 56))

def draw_webcam_pip(surface, cam_frame, hand_found, head_norm_y):
    pip_w, pip_h = 110, 82
    pip_x = WIDTH - pip_w - 14
    pip_y = 14

    shadow_rect = pygame.Rect(pip_x + 3, pip_y + 3, pip_w, pip_h)
    pygame.draw.rect(surface, (10, 20, 30, 100), shadow_rect, border_radius=8)

    if cam_frame is not None:
        rgb_small = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        rgb_resized = cv2.resize(rgb_small, (pip_w, pip_h))
        cam_surf = pygame.image.frombuffer(rgb_resized.tobytes(), (pip_w, pip_h), 'RGB')
        surface.blit(cam_surf, (pip_x, pip_y))

    border_color = (60, 230, 90) if hand_found else (240, 70, 70)
    pygame.draw.rect(surface, border_color, (pip_x, pip_y, pip_w, pip_h), 2, border_radius=6)

    status_bg = pygame.Surface((pip_w, 18), pygame.SRCALPHA)
    status_bg.fill((0, 0, 0, 160))
    surface.blit(status_bg, (pip_x, pip_y + pip_h - 18))

    status_str = "● MANO OK" if hand_found else "! MOSTRAR MANO"
    status_col = (100, 255, 120) if hand_found else (255, 140, 100)
    txt_status = font_small.render(status_str, True, status_col)
    surface.blit(txt_status, (pip_x + 6, pip_y + pip_h - 17))

    bar_x = pip_x - 14
    bar_y = pip_y
    bar_h = pip_h
    pygame.draw.rect(surface, (30, 40, 50), (bar_x, bar_y, 8, bar_h), border_radius=4)
    pygame.draw.rect(surface, WHITE, (bar_x, bar_y, 8, bar_h), 1, border_radius=4)

    if head_norm_y is not None:
        min_c, max_c = 0.15, 0.80
        ratio = (head_norm_y - min_c) / (max_c - min_c)
        ratio = max(0.0, min(1.0, ratio))
        indicator_y = int(bar_y + ratio * (bar_h - 8))
        pygame.draw.circle(surface, border_color, (bar_x + 4, indicator_y + 4), 6)
        pygame.draw.circle(surface, WHITE, (bar_x + 4, indicator_y + 4), 3)

def draw_hall_of_fame_panel(surface, highlight_initials="", highlight_score=0):
    panel = pygame.Surface((340, 320), pygame.SRCALPHA)
    panel.fill((15, 20, 35, 245))
    pygame.draw.rect(panel, GOLD, (0, 0, 340, 320), 3, border_radius=14)

    t_title = font_title.render("SALÓN DE LA FAMA", True, GOLD)
    panel.blit(t_title, (170 - t_title.get_width() // 2, 16))

    records = []
    if os.path.exists(WINNERS_FILE):
        try:
            with open(WINNERS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "Iniciales:" in line and "Puntos:" in line:
                        parts = line.strip().split("|")
                        init_p = parts[0].split(":")[1].strip()
                        score_p = int(parts[1].split(":")[1].strip())
                        records.append((init_p, score_p))
        except Exception:
            pass

    records.sort(key=lambda x: x[1], reverse=True)
    records = records[:5]

    y_off = 70
    if not records:
        t_empty = font_small.render("Aún no hay ganadores registrados.", True, WHITE)
        panel.blit(t_empty, (170 - t_empty.get_width() // 2, y_off + 40))
    else:
        for idx, (inits, sc) in enumerate(records):
            is_current = (inits == highlight_initials and sc == highlight_score)
            col = GOLD if is_current else WHITE
            t_rank = font_mid.render(f"#{idx + 1}   {inits}   -   {sc} pts", True, col)
            panel.blit(t_rank, (170 - t_rank.get_width() // 2, y_off))
            y_off += 38

    t_close = font_small.render("Presiona ESPACIO o R para reiniciar", True, (130, 240, 160))
    panel.blit(t_close, (170 - t_close.get_width() // 2, 280))

    surface.blit(panel, (WIDTH // 2 - 170, HEIGHT // 2 - 160))

# ---------------------------------------------------------
# 7. Bucle Principal y Lógica del Juego
# ---------------------------------------------------------
def main():
    global sounds_enabled, screen, fullscreen
    high_score = get_high_score()
    clouds = [Cloud(x, layer=1) for x in range(0, WIDTH + 100, 120)]
    clouds += [Cloud(x, layer=2) for x in range(30, WIDTH + 100, 160)]
    stars = [(random.randint(5, WIDTH - 5), random.randint(15, HEIGHT - 110), random.uniform(1.0, 2.2)) for _ in range(40)]

    state = "START"  # "START", "PLAYING", "LEVEL_COMPLETE", "VICTORY", "GAME_OVER"
    bird = Bird()
    active_mode = "CAMPAIGN"  # "CAMPAIGN" o "INFINITE"
    current_level_idx = 0
    pipes = []
    coins = []
    particles = []
    confetti_particles = []
    floating_texts = []

    score = 0
    pipes_spawned = 0
    pipes_cleared = 0
    current_dynamic_speed = 5.0
    current_dynamic_gap = 175
    ground_scroll = 0
    shake_timer = 0
    star_timer = 0
    has_broken_record = False
    is_paused = False
    show_pip = True
    player_initials = ""
    initials_saved = False
    showing_hall_of_fame = False

    def init_level(idx_or_mode):
        nonlocal current_level_idx, active_mode, pipes_spawned, pipes_cleared, pipes, coins, player_initials, initials_saved, current_dynamic_speed, current_dynamic_gap
        
        if idx_or_mode == "INFINITE":
            active_mode = "INFINITE"
            lvl = INFINITE_LEVEL
        else:
            active_mode = "CAMPAIGN"
            current_level_idx = idx_or_mode
            lvl = CAMPAIGN_LEVELS[current_level_idx]

        pipes_spawned = 1
        pipes_cleared = 0
        current_dynamic_speed = lvl["speed"]
        current_dynamic_gap = lvl["gap"]
        pipes = [Pipe(WIDTH + 80, current_dynamic_speed, gap=current_dynamic_gap, is_moving=False, colors=lvl["pipe_colors"])]
        coins.clear()
        bird.target_y = HEIGHT // 2
        if idx_or_mode == 0 or idx_or_mode == "INFINITE":
            player_initials = ""
            initials_saved = False

    while True:
        dt = clock.tick(60)
        star_timer += 0.05
        current_level = INFINITE_LEVEL if active_mode == "INFINITE" else CAMPAIGN_LEVELS[current_level_idx]

        # 1. Eventos de Pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    cap.release()
                    pygame.quit()
                    sys.exit()

                # Control para alternar Pantalla Completa
                if event.key in (pygame.K_F11, pygame.K_f):
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

                # Registrar iniciales tras Victoria
                if state == "VICTORY" and not initials_saved:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if len(player_initials.strip()) > 0:
                            save_winner_initials(player_initials, score)
                            initials_saved = True
                            play_sfx(sound_record)
                            floating_texts.append(FloatingText(WIDTH // 2, 80, "¡GUARDADO!", (120, 255, 150)))
                    elif event.key == pygame.K_BACKSPACE:
                        player_initials = player_initials[:-1]
                    else:
                        char = event.unicode.upper()
                        if len(player_initials) < 3 and char.isalnum():
                            player_initials += char
                    continue

                if event.key == pygame.K_p and state == "PLAYING":
                    is_paused = not is_paused
                if event.key == pygame.K_m:
                    sounds_enabled = not sounds_enabled
                    floating_texts.append(FloatingText(WIDTH // 2, 90, "AUDIO: ON" if sounds_enabled else "AUDIO: OFF", WHITE))
                if event.key == pygame.K_c:
                    show_pip = not show_pip
                if event.key == pygame.K_t:
                    showing_hall_of_fame = not showing_hall_of_fame

                # SELECCIÓN DE MODO DESDE LA PANTALLA DE INICIO
                if state == "START":
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        score = 0
                        init_level(0)
                        state = "PLAYING"
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        score = 0
                        init_level("INFINITE")
                        state = "PLAYING"
                    elif event.key == pygame.K_SPACE:
                        score = 0
                        init_level(0)
                        state = "PLAYING"

                # Avanzar al siguiente nivel en Modo Campaña
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN) and state == "LEVEL_COMPLETE":
                    if current_level_idx + 1 < len(CAMPAIGN_LEVELS):
                        init_level(current_level_idx + 1)
                        confetti_particles.clear()
                        state = "PLAYING"

                # Reiniciar partida
                elif event.key in (pygame.K_r, pygame.K_SPACE) and (state == "GAME_OVER" or (state == "VICTORY" and initials_saved)):
                    bird = Bird()
                    particles.clear()
                    confetti_particles.clear()
                    floating_texts.clear()
                    shake_timer = 0
                    is_paused = False
                    showing_hall_of_fame = False
                    if state == "VICTORY":
                        score = 0
                        init_level(0)
                    else:
                        init_level("INFINITE" if active_mode == "INFINITE" else current_level_idx)
                    state = "PLAYING"

                # Volver a selección de modo (Pantalla de inicio)
                elif event.key == pygame.K_1 and state == "GAME_OVER":
                    bird = Bird()
                    particles.clear()
                    confetti_particles.clear()
                    floating_texts.clear()
                    shake_timer = 0
                    is_paused = False
                    showing_hall_of_fame = False
                    score = 0
                    state = "START"

        # 2. Captura y Detección de Mano con MediaPipe
        ret, frame = cap.read()
        detected_y_norm = None
        hand_found = False
        display_frame = None

        if ret:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = hand_detector.detect(mp_image)

            display_frame = frame.copy()
            if detection_result.hand_landmarks and len(detection_result.hand_landmarks) > 0:
                hand_found = True
                hand_lms = detection_result.hand_landmarks[0]
                fh, fw = frame.shape[:2]

                pts = [(int(lm.x * fw), int(lm.y * fh)) for lm in hand_lms]

                for start_idx, end_idx in HAND_CONNECTIONS:
                    cv2.line(display_frame, pts[start_idx], pts[end_idx], (0, 255, 120), 2)
                for pt in pts:
                    cv2.circle(display_frame, pt, 3, (0, 220, 255), -1)

                palm_pt = pts[9]
                cv2.circle(display_frame, palm_pt, 6, (0, 120, 255), -1)
                cv2.circle(display_frame, palm_pt, 9, (255, 255, 255), 2)

                detected_y_norm = hand_lms[9].y

        # 3. Lógica de Estados
        for c in clouds:
            c.update()

        if state == "START":
            bird.update(detected_y_norm)
            ground_scroll += 1.5

        elif state == "PLAYING":
            if not is_paused:
                bird.update(detected_y_norm)
                ground_scroll += current_dynamic_speed

                if random.random() < 0.4:
                    particles.append(Particle(
                        bird.x - 14, bird.y + random.randint(-4, 4),
                        vx=-random.uniform(1.5, 3.0), vy=random.uniform(-0.6, 0.6),
                        color=(255, 245, 170), size=4, lifetime=22
                    ))

                for pipe in pipes:
                    pipe.speed = current_dynamic_speed
                    pipe.update()

                    if pipe.collide(bird):
                        state = "GAME_OVER"
                        shake_timer = 18
                        play_sfx(sound_hit)
                        for _ in range(25):
                            particles.append(Particle(
                                bird.x, bird.y,
                                vx=random.uniform(-4, 4), vy=random.uniform(-5, 3),
                                color=random.choice([YELLOW_BIRD, ORANGE_BEAK, WHITE, (255, 230, 90)]),
                                size=random.randint(4, 7), lifetime=35
                            ))
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)

                    if not pipe.passed and pipe.x + pipe.width < bird.x:
                        pipe.passed = True
                        score += 1
                        pipes_cleared += 1
                        floating_texts.append(FloatingText(bird.x + 20, bird.y - 20, "+1"))

                        # Aumentar velocidad cada 5 tuberías en Modo Infinito
                        if current_level.get("infinite", False) and pipes_cleared % 5 == 0:
                            current_dynamic_speed += 0.6
                            current_dynamic_gap = max(130, current_dynamic_gap - 2)
                            floating_texts.append(FloatingText(WIDTH // 2, 120, "¡MÁS RÁPIDO! ⚡", RED))
                            play_sfx(sound_record)

                        if score > high_score and not has_broken_record and high_score > 0:
                            has_broken_record = True
                            play_sfx(sound_record)
                            floating_texts.append(FloatingText(bird.x + 20, bird.y - 45, "¡NUEVO RÉCORD!", GOLD))
                        else:
                            play_sfx(sound_score)

                for coin in coins:
                    coin.update(current_dynamic_speed)
                    if not coin.collected and coin.collide(bird):
                        coin.collected = True
                        score += 2
                        play_sfx(sound_coin)
                        floating_texts.append(FloatingText(coin.x, coin.y - 15, "+2", GOLD))
                        for _ in range(14):
                            particles.append(Particle(
                                coin.x, coin.y,
                                vx=random.uniform(-3, 3), vy=random.uniform(-3.5, 2),
                                color=random.choice([GOLD, (255, 245, 170), WHITE]),
                                size=random.randint(3, 5), lifetime=25
                            ))

                coins = [c for c in coins if not c.collected and c.x > -30]

                target_pipes = current_level["target_pipes"]
                if pipes and pipes[-1].x < WIDTH - 250 and pipes_spawned < target_pipes:
                    is_moving = (random.random() < current_level["moving_prob"])
                    new_pipe = Pipe(
                        WIDTH + 20, current_dynamic_speed,
                        gap=current_dynamic_gap,
                        is_moving=is_moving,
                        colors=current_level["pipe_colors"]
                    )
                    pipes.append(new_pipe)
                    pipes_spawned += 1

                    if random.random() < 0.70:
                        coin_y = new_pipe.top_height + new_pipe.gap // 2
                        coins.append(Coin(new_pipe.x + new_pipe.width // 2, coin_y))

                if pipes and pipes[0].x < -pipes[0].width - 15:
                    pipes.pop(0)

                if (bird.y - bird.radius <= 0) or (bird.y + bird.radius >= HEIGHT - 70):
                    state = "GAME_OVER"
                    shake_timer = 18
                    play_sfx(sound_hit)
                    for _ in range(25):
                        particles.append(Particle(
                            bird.x, bird.y,
                            vx=random.uniform(-4, 4), vy=random.uniform(-4, 3),
                            color=random.choice([YELLOW_BIRD, ORANGE_BEAK, WHITE]),
                            size=random.randint(4, 7), lifetime=35
                        ))
                    if score > high_score:
                        high_score = score
                        save_high_score(high_score)

                if not current_level.get("infinite", False) and pipes_cleared >= target_pipes and len(pipes) == 0:
                    if current_level_idx < len(CAMPAIGN_LEVELS) - 1:
                        state = "LEVEL_COMPLETE"
                        play_sfx(sound_win)
                        for _ in range(50):
                            confetti_particles.append(Confetti(random.randint(40, WIDTH - 40), random.randint(40, 200)))
                    else:
                        state = "VICTORY"
                        play_sfx(sound_win)
                        for _ in range(80):
                            confetti_particles.append(Confetti(random.randint(40, WIDTH - 40), random.randint(40, 200)))
                        if score > high_score:
                            high_score = score
                            save_high_score(high_score)

        elif state == "LEVEL_COMPLETE":
            bird.update(detected_y_norm)
            ground_scroll += 1.5

        elif state == "VICTORY":
            bird.update(detected_y_norm)
            ground_scroll += 1.5
            if random.random() < 0.25:
                confetti_particles.append(Confetti(random.randint(20, WIDTH - 20), 20))

        elif state == "GAME_OVER":
            if bird.y < HEIGHT - 70 - bird.radius:
                bird.y += 6
                bird.angle = min(75, bird.angle + 5)

        particles = [p for p in particles if p.update()]
        confetti_particles = [cp for cp in confetti_particles if cp.update()]
        floating_texts = [ft for ft in floating_texts if ft.update()]

        # 4. Renderizado
        game_surface = pygame.Surface((WIDTH, HEIGHT))

        draw_background(game_surface, current_level)
        if current_level.get("night"):
            draw_stars(game_surface, stars, star_timer)

        for c in clouds:
            c.draw(game_surface)

        for pipe in pipes:
            pipe.draw(game_surface)

        for coin in coins:
            coin.draw(game_surface)

        draw_ground(game_surface, ground_scroll, is_night=current_level.get("night", False))

        for p in particles:
            p.draw(game_surface)

        for cp in confetti_particles:
            cp.draw(game_surface)

        bird.draw(game_surface)

        for ft in floating_texts:
            ft.draw(game_surface)

        if state in ("PLAYING", "START", "LEVEL_COMPLETE"):
            draw_hud(game_surface, current_level, pipes_cleared, score, high_score)

        if show_pip:
            draw_webcam_pip(game_surface, display_frame, hand_found, detected_y_norm)

        if is_paused and state == "PLAYING":
            pause_panel = pygame.Surface((280, 110), pygame.SRCALPHA)
            pause_panel.fill((20, 25, 35, 220))
            pygame.draw.rect(pause_panel, WHITE, (0, 0, 280, 110), 2, border_radius=12)
            t_p1 = font_title.render("PAUSA", True, GOLD)
            t_p2 = font_small.render("Presiona 'P' para continuar", True, (200, 230, 255))
            pause_panel.blit(t_p1, (140 - t_p1.get_width() // 2, 16))
            pause_panel.blit(t_p2, (140 - t_p2.get_width() // 2, 70))
            game_surface.blit(pause_panel, (WIDTH // 2 - 140, HEIGHT // 2 - 55))

        # Pantalla de Selección de Modo de Juego
        if state == "START":
            start_panel = pygame.Surface((350, 225), pygame.SRCALPHA)
            start_panel.fill((20, 30, 40, 220))
            pygame.draw.rect(start_panel, WHITE, (0, 0, 350, 225), 2, border_radius=12)

            t1 = font_mid.render("¡FLAPPY BIRD - CONTROL POR MANO!", True, GOLD)
            t2 = font_small.render("Muestra tu mano y muévela arriba y abajo", True, WHITE)
            t_m1 = font_mid.render("[1] MODO CAMPAÑA (3 Niveles)", True, (110, 240, 140))
            t_m2 = font_mid.render("[2] MODO INFINITO (Aumenta v)", True, (255, 120, 120))
            t5 = font_small.render("P: Pausa | M: Audio | C: Cámara | T: Récords", True, (180, 210, 240))
            t6 = font_small.render("F11 o F: Alternar Pantalla Completa", True, (255, 215, 120))

            start_panel.blit(t1, (175 - t1.get_width() // 2, 12))
            start_panel.blit(t2, (175 - t2.get_width() // 2, 40))
            start_panel.blit(t_m1, (175 - t_m1.get_width() // 2, 72))
            start_panel.blit(t_m2, (175 - t_m2.get_width() // 2, 104))
            start_panel.blit(t5, (175 - t5.get_width() // 2, 150))
            start_panel.blit(t6, (175 - t6.get_width() // 2, 180))
            game_surface.blit(start_panel, (WIDTH // 2 - 175, HEIGHT // 2 - 80))

        elif state == "LEVEL_COMPLETE":
            lvl_panel = pygame.Surface((340, 210), pygame.SRCALPHA)
            lvl_panel.fill((15, 30, 45, 235))
            pygame.draw.rect(lvl_panel, GOLD, (0, 0, 340, 210), 3, border_radius=14)

            t_win = font_title.render("¡NIVEL SUPERADO!", True, GOLD)
            t_comp = font_small.render(f"Superaste el {current_level['name']}", True, WHITE)
            next_lvl = CAMPAIGN_LEVELS[current_level_idx + 1]
            t_next = font_small.render(f"Siguiente: {next_lvl['name']}", True, (255, 205, 120))
            t_desc = font_small.render(next_lvl['subtitle'], True, (190, 230, 255))
            t_btn = font_mid.render("Presiona ESPACIO para seguir", True, (100, 255, 140))

            lvl_panel.blit(t_win, (170 - t_win.get_width() // 2, 18))
            lvl_panel.blit(t_comp, (170 - t_comp.get_width() // 2, 70))
            lvl_panel.blit(t_next, (170 - t_next.get_width() // 2, 98))
            lvl_panel.blit(t_desc, (170 - t_desc.get_width() // 2, 124))
            lvl_panel.blit(t_btn, (170 - t_btn.get_width() // 2, 160))
            game_surface.blit(lvl_panel, (WIDTH // 2 - 170, HEIGHT // 2 - 105))

        elif state == "VICTORY":
            if not initials_saved:
                vic_panel = pygame.Surface((350, 255), pygame.SRCALPHA)
                vic_panel.fill((20, 25, 45, 245))
                pygame.draw.rect(vic_panel, GOLD, (0, 0, 350, 255), 4, border_radius=16)

                t_vic = font_title.render("¡VICTORIA TOTAL!", True, GOLD)
                t_sub = font_small.render("¡Has completado el modo campaña!", True, WHITE)
                t_pts = font_mid.render(f"PUNTOS FINALES: {score}", True, (100, 255, 140))
                t_reg = font_small.render("REGISTRA TUS INICIALES:", True, (255, 230, 140))

                box_rect = pygame.Rect(75, 148, 200, 48)
                pygame.draw.rect(vic_panel, (10, 15, 28), box_rect, border_radius=8)
                pygame.draw.rect(vic_panel, GOLD, box_rect, 2, border_radius=8)

                chars = list(player_initials.ljust(3, "_"))
                cursor_visible = (int(star_timer * 6) % 2 == 0) and len(player_initials) < 3
                if cursor_visible:
                    chars[len(player_initials)] = "|"
                display_str = "   ".join(chars)
                txt_initials = font_score.render(display_str, True, WHITE)
                vic_panel.blit(txt_initials, (175 - txt_initials.get_width() // 2, 150))

                if len(player_initials.strip()) > 0:
                    t_hint = font_small.render("Presiona ENTER para guardar récord", True, (100, 255, 140))
                else:
                    t_hint = font_small.render("Escribe tus letras en el teclado", True, (180, 220, 255))
                vic_panel.blit(t_hint, (175 - t_hint.get_width() // 2, 212))
                vic_panel.blit(t_vic, (175 - t_vic.get_width() // 2, 16))
                vic_panel.blit(t_sub, (175 - t_sub.get_width() // 2, 58))
                vic_panel.blit(t_pts, (175 - t_pts.get_width() // 2, 86))
                vic_panel.blit(t_reg, (175 - t_reg.get_width() // 2, 120))
                game_surface.blit(vic_panel, (WIDTH // 2 - 175, HEIGHT // 2 - 128))
            else:
                draw_hall_of_fame_panel(game_surface, highlight_initials=player_initials, highlight_score=score)

        elif state == "GAME_OVER":
            over_panel = pygame.Surface((330, 230), pygame.SRCALPHA)
            over_panel.fill((25, 20, 30, 235))
            pygame.draw.rect(over_panel, (240, 70, 70), (0, 0, 330, 230), 3, border_radius=14)

            t_over = font_title.render("GAME OVER", True, (255, 85, 85))
            t_target_txt = "∞" if current_level.get("infinite", False) else str(current_level['target_pipes'])
            t_lvl_prog = font_small.render(f"{current_level['name']}: {pipes_cleared}/{t_target_txt} tubos", True, WHITE)
            t_score = font_mid.render(f"PUNTOS: {score}  |  RÉCORD: {high_score}", True, GOLD)
            t_retry = font_small.render("ESPACIO o 'R': Reintentar", True, (130, 240, 160))
            t_reset = font_small.render("Presiona '1': Volver al Menú Principal", True, (180, 210, 240))

            over_panel.blit(t_over, (165 - t_over.get_width() // 2, 18))
            over_panel.blit(t_lvl_prog, (165 - t_lvl_prog.get_width() // 2, 74))
            over_panel.blit(t_score, (165 - t_score.get_width() // 2, 108))
            over_panel.blit(t_retry, (165 - t_retry.get_width() // 2, 148))
            over_panel.blit(t_reset, (165 - t_reset.get_width() // 2, 180))
            game_surface.blit(over_panel, (WIDTH // 2 - 165, HEIGHT // 2 - 115))

        if showing_hall_of_fame:
            draw_hall_of_fame_panel(game_surface)

        offset_x, offset_y = 0, 0
        if shake_timer > 0:
            shake_intensity = int(shake_timer * 0.45)
            offset_x = random.randint(-shake_intensity, shake_intensity)
            offset_y = random.randint(-shake_intensity, shake_intensity)
            shake_timer -= 1

        screen.fill(BLACK)
        screen_w, screen_h = screen.get_size()
        scale = min(screen_w / WIDTH, screen_h / HEIGHT)
        new_w, new_h = int(WIDTH * scale), int(HEIGHT * scale)

        scaled_surface = pygame.transform.smoothscale(game_surface, (new_w, new_h))
        pos_x = (screen_w - new_w) // 2 + offset_x
        pos_y = (screen_h - new_h) // 2 + offset_y

        screen.blit(scaled_surface, (pos_x, pos_y))
        pygame.display.flip()

if __name__ == "__main__":
    main()