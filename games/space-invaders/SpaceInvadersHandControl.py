import pygame
import cv2
import mediapipe as mp
import random
import math
import time
import json
import os

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Standard MediaPipe hand topology (21 landmarks) used to draw the skeleton
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),                      # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),                      # index
    (9, 10), (10, 11), (11, 12),                         # middle
    (13, 14), (14, 15), (15, 16),                        # ring
    (0, 17), (17, 18), (18, 19), (19, 20),               # pinky
    (5, 9), (9, 13), (13, 17),                           # palm
]

# --- Configuración de Mediapipe (Tasks API, mediapipe 1.2.3) ---
hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="hand_landmarker.task"),
    running_mode=vision.RunningMode.IMAGE,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_tracking_confidence=0.5
))

# --- Inicialización de Pygame ---
pygame.init()
screen_info = pygame.display.Info()
SCREEN_WIDTH = screen_info.current_w
SCREEN_HEIGHT = screen_info.current_h
# Pantalla completa
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Space Invaders: Feria Grand Finale")

# Colores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (200, 0, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)

# --- Carga y ESCALADO de recursos ---
SCALE_FACTOR = 2.0 

def scale_img(img, factor):
    w, h = img.get_size()
    return pygame.transform.scale(img, (int(w * factor), int(h * factor)))

try:
    background_img = pygame.image.load("Recursos/SpaceBackGround.png").convert()
    background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
    ship_img = scale_img(pygame.image.load("Recursos/SpaceShip.png").convert_alpha(), SCALE_FACTOR)
    alien1_img = scale_img(pygame.image.load("Recursos/Alien-001.png").convert_alpha(), SCALE_FACTOR)
    alien2_img = scale_img(pygame.image.load("Recursos/Alien-002.png").convert_alpha(), SCALE_FACTOR)
    bullet_img = scale_img(pygame.image.load("Recursos/Bullet.png").convert_alpha(), SCALE_FACTOR)
except:
    ship_img = pygame.Surface((100, 80)); ship_img.fill(GREEN)
    alien1_img = pygame.Surface((80, 60)); alien1_img.fill(CYAN)
    alien2_img = pygame.Surface((80, 60)); alien2_img.fill(YELLOW)
    bullet_img = pygame.Surface((10, 30)); bullet_img.fill(WHITE)
    background_img = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); background_img.fill(BLACK)

# --- Gestión de Puntajes ---
HIGHSCORE_FILE = "highscores.json"
def load_scores():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return sorted(json.load(f), key=lambda x: x['score'], reverse=True)[:5]
        except: return []
    return []

def save_score(name, score):
    s = load_scores()
    s.append({"name": name.upper(), "score": score})
    s = sorted(s, key=lambda x: x['score'], reverse=True)[:5]
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(s, f)

# --- Clases del Juego ---

class Bullet:
    def __init__(self, x, y, speed):
        self.image = bullet_img.copy()
        if speed > 0: # Bala enemiga
            self.image = pygame.transform.flip(self.image, False, True)
            self.image.fill((255, 100, 100), special_flags=pygame.BLEND_MULT)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Fireball:
    def __init__(self, x, y, angle, speed):
        self.image = pygame.Surface((35, 35), pygame.SRCALPHA)
        pygame.draw.circle(self.image, ORANGE, (17, 17), 17)
        pygame.draw.circle(self.image, WHITE, (17, 17), 9)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy

    def is_offscreen(self):
        return (self.rect.x < -100 or self.rect.x > SCREEN_WIDTH + 100 or 
                self.rect.y < -100 or self.rect.y > SCREEN_HEIGHT + 100)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Beam:
    def __init__(self, x, y_start):
        self.rect = pygame.Rect(x - 12, y_start, 24, SCREEN_HEIGHT - y_start)
        self.spawn_time = time.time()

    def is_expired(self):
        return time.time() - self.spawn_time > 0.6

    def draw(self, surface):
        color = PURPLE if int(time.time() * 20) % 2 == 0 else WHITE
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect.inflate(-8, 0))

class Player:
    def __init__(self):
        self.image = ship_img
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 60
        self.lives = 3
        self.last_shot = 0
        self.shot_delay = 0.5 
        self.invulnerable_until = 0
        self.hit_until = 0

    def move(self, tx):
        target = (1.0 - tx) * SCREEN_WIDTH
        self.rect.centerx += (target - self.rect.centerx) * 0.18
        self.rect.left = max(0, min(self.rect.left, SCREEN_WIDTH - self.rect.width))

    def shoot(self, b_list):
        if time.time() - self.last_shot > self.shot_delay:
            b_list.append(Bullet(self.rect.centerx, self.rect.top, -18))
            self.last_shot = time.time()

    def draw(self, surface):
        if time.time() < self.invulnerable_until and int(time.time() * 10) % 2 == 0:
            return
        img = self.image
        if time.time() < self.hit_until:
            img = self.image.copy()
            img.fill(WHITE, special_flags=pygame.BLEND_ADD)
        surface.blit(img, self.rect)

class Enemy:
    def __init__(self, x, y, alien_type="NORMAL"):
        self.type = alien_type
        self.hit_until = 0
        
        if self.type == "BOSS":
            self.image = pygame.transform.scale(alien2_img, (int(alien2_img.get_width()*2), int(alien2_img.get_height()*2)))
            self.lives = 10
            self.spiral_angle = 0
            self.last_burst = 0
        elif self.type == "TOUGH":
            self.image = alien2_img
            self.lives = 2
            self.burst_queued = 0
            self.last_burst_shot = 0
        elif self.type == "BEAMER":
            self.image = alien1_img.copy()
            self.image.fill(PURPLE, special_flags=pygame.BLEND_MULT)
            self.lives = 1
        else:
            self.image = alien1_img
            self.lives = 1
            
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = 1
        self.speed = 2.0 
        self.state = "IDLE" # IDLE, CHARGING, DIVING
        self.charge_start = 0
        self.dive_speed = 8.0

    def update(self, e_bullets, beams, fireballs, player_pos, level):
        if self.state == "DIVING":
            target_x, target_y = player_pos
            angle = math.atan2(target_y - self.rect.y, target_x - self.rect.x)
            self.rect.x += math.cos(angle) * self.dive_speed
            self.rect.y += math.sin(angle) * self.dive_speed
            if self.rect.top > SCREEN_HEIGHT:
                self.rect.y = -50
                self.state = "IDLE"
            return 

        if self.type == "BOSS":
            self.rect.x += (self.speed * 0.8) * self.direction
            if self.rect.right > SCREEN_WIDTH - 150 or self.rect.left < 150:
                self.direction *= -1
            if time.time() - self.last_burst > 1.2:
                for i in range(8):
                    angle = self.spiral_angle + (i * math.pi / 4)
                    fireballs.append(Fireball(self.rect.centerx, self.rect.centery, angle, 6))
                self.spiral_angle += 0.3
                self.last_burst = time.time()
        else:
            self.rect.x += self.speed * self.direction

        if self.type == "NORMAL" and level in [2, 3] and self.state == "IDLE":
            if random.random() < 0.0005: self.state = "DIVING"

        if self.type == "TOUGH":
            if self.burst_queued > 0:
                if time.time() - self.last_burst_shot > 0.2:
                    e_bullets.append(Bullet(self.rect.centerx, self.rect.bottom, 7))
                    self.last_burst_shot = time.time()
                    self.burst_queued -= 1
            elif random.random() < 0.002 and len(e_bullets) < 5:
                self.burst_queued = 2
                self.last_burst_shot = 0
        elif self.type == "BEAMER":
            if self.state == "IDLE":
                if random.random() < 0.002:
                    self.state = "CHARGING"
                    self.charge_start = time.time()
            elif self.state == "CHARGING":
                if time.time() - self.charge_start > 1.5:
                    beams.append(Beam(self.rect.centerx, self.rect.bottom))
                    self.state = "IDLE"
        elif self.type == "NORMAL" and self.state == "IDLE":
            if random.random() < 0.001 and len(e_bullets) < 4:
                e_bullets.append(Bullet(self.rect.centerx, self.rect.bottom, 6))

    def draw(self, surface):
        img = self.image
        if self.state == "CHARGING":
            if int(time.time() * 10) % 2 != 0:
                img = self.image.copy()
                img.fill(RED, special_flags=pygame.BLEND_MULT)
        if self.state == "DIVING":
            img = self.image.copy()
            img.fill(ORANGE, special_flags=pygame.BLEND_ADD)
        if time.time() < self.hit_until:
            img = img.copy()
            img.fill(WHITE, special_flags=pygame.BLEND_ADD)
        surface.blit(img, self.rect)

# --- Bucle Principal ---

def main():
    cap = cv2.VideoCapture(0)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 36, bold=True)
    big_f = pygame.font.SysFont("Arial", 90, bold=True)
    
    state = "PLAYING"
    level = 1
    score = 0
    player = Player()
    player_name = ""
    
    def spawn_enemies(lvl):
        ents = []
        if lvl == 4:
            ents.append(Enemy(SCREEN_WIDTH//2, 250, "BOSS"))
            return ents
        spacing_x, spacing_y = 150, 110
        margin_x = (SCREEN_WIDTH - (5 * spacing_x)) // 2
        for row in range(3):
            for col in range(6):
                etype = "NORMAL"
                if lvl == 2 and row == 0: etype = "TOUGH"
                elif lvl >= 3:
                    if row == 0: etype = "BEAMER"
                    elif row == 1: etype = "TOUGH"
                ents.append(Enemy(margin_x + col * spacing_x, 120 + row * spacing_y, etype))
        return ents

    enemies = spawn_enemies(level)
    player_bullets, enemy_bullets, beams, fireballs = [], [], [], []

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                cap.release(); pygame.quit(); return
            if state == "INPUT_NAME" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and player_name:
                    save_score(player_name, score); state = "HIGH_SCORES"
                elif event.key == pygame.K_BACKSPACE: player_name = player_name[:-1]
                elif len(player_name) < 3 and event.unicode.isalpha(): player_name += event.unicode.upper()
            elif state == "HIGH_SCORES" and event.type == pygame.KEYDOWN:
                main(); return

        if state == "PLAYING":
            success, frame = cap.read()
            if not success: break
            frame = cv2.flip(frame, 1)
            res = hands.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            hx, pinch = 0.5, False
            fh, fw = frame.shape[:2]
            for hl in res.hand_landmarks:
                for a, b in HAND_CONNECTIONS:
                    cv2.line(frame, (int(hl[a].x*fw), int(hl[a].y*fh)), (int(hl[b].x*fw), int(hl[b].y*fh)), (0, 255, 0), 2)
                for lm in hl:
                    cv2.circle(frame, (int(lm.x*fw), int(lm.y*fh)), 4, (0, 0, 255), -1)
                hx = 1.0 - hl[9].x
                d = math.sqrt((hl[4].x-hl[8].x)**2 + (hl[4].y-hl[8].y)**2)
                if d < 0.06: pinch = True
            
            player.move(hx)
            if pinch: player.shoot(player_bullets)

            # Update Balas
            for b in player_bullets[:]:
                b.update()
                if b.rect.bottom < 0: player_bullets.remove(b)
            for b in enemy_bullets[:]:
                b.update()
                if b.rect.top > SCREEN_HEIGHT: enemy_bullets.remove(b)
                if b.rect.colliderect(player.rect) and time.time() > player.invulnerable_until:
                    player.lives -= 1; player.invulnerable_until = time.time() + 2; player.hit_until = time.time() + 0.1
                    if b in enemy_bullets: enemy_bullets.remove(b)
            for fb in fireballs[:]:
                fb.update()
                if fb.is_offscreen(): fireballs.remove(fb)
                elif fb.rect.colliderect(player.rect) and time.time() > player.invulnerable_until:
                    player.lives -= 1; player.invulnerable_until = time.time() + 2; player.hit_until = time.time() + 0.1
                    fireballs.remove(fb)
            for bm in beams[:]:
                if bm.is_expired(): beams.remove(bm)
                elif bm.rect.colliderect(player.rect) and time.time() > player.invulnerable_until:
                    player.lives -= 2; player.invulnerable_until = time.time() + 2; player.hit_until = time.time() + 0.1
            
            if player.lives <= 0: state = "INPUT_NAME"

            # Update Enemigos
            edge = False
            SIDE_LIMIT = SCREEN_WIDTH // 5
            for e in enemies:
                e.update(enemy_bullets, beams, fireballs, player.rect.center, level)
                if e.state != "DIVING" and e.type != "BOSS":
                    if e.rect.right > (SCREEN_WIDTH - SIDE_LIMIT) or e.rect.left < SIDE_LIMIT: edge = True
                if e.rect.colliderect(player.rect):
                    if time.time() > player.invulnerable_until:
                        player.lives -= 1; player.invulnerable_until = time.time() + 2; player.hit_until = time.time() + 0.1
                    if e.state == "DIVING": enemies.remove(e)

            if edge:
                for e in enemies:
                    if e.state != "DIVING": e.direction *= -1; e.rect.y += 15

            # Colisiones Balas-Enemigos
            for pb in player_bullets[:]:
                for e in enemies[:]:
                    if pb.rect.colliderect(e.rect):
                        e.lives -= 1; e.hit_until = time.time() + 0.1
                        if pb in player_bullets: player_bullets.remove(pb)
                        if e.lives <= 0: 
                            enemies.remove(e); score += (500 if e.type == "BOSS" else 300 * level)
                        break

            if not enemies:
                level += 1
                if level > 4: state = "INPUT_NAME"
                else:
                    enemies = spawn_enemies(level)
                    player_bullets, enemy_bullets, beams, fireballs = [], [], [], []

        # Renderizado
        screen.blit(background_img, (0, 0))
        if state == "PLAYING":
            player.draw(screen)
            for e in enemies: e.draw(screen)
            for b in player_bullets + enemy_bullets: b.draw(screen)
            for bm in beams: bm.draw(screen)
            for fb in fireballs: fb.draw(screen)
            txt_l = "FINAL BOSS" if level == 4 else f"LEVEL: {level}"
            screen.blit(font.render(f"SCORE: {score}", True, YELLOW), (50, 50))
            screen.blit(font.render(txt_l, True, CYAN), (50, 100))
            screen.blit(font.render(f"LIVES: {player.lives}", True, GREEN if player.lives > 1 else RED), (50, 150))
            cam_s = pygame.surfarray.make_surface(cv2.cvtColor(cv2.resize(frame, (250, 180)), cv2.COLOR_BGR2RGB).swapaxes(0, 1))
            screen.blit(cam_s, (SCREEN_WIDTH - 290, SCREEN_HEIGHT - 230))
        elif state == "INPUT_NAME":
            title = "LEGENDARY VICTORY!" if level > 4 else "GAME OVER"
            txt = big_f.render(title, True, GREEN if level > 4 else RED)
            screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, SCREEN_HEIGHT//4))
            name_txt = big_f.render(player_name + "_" * (3 - len(player_name)), True, GREEN)
            screen.blit(name_txt, (SCREEN_WIDTH//2 - name_txt.get_width()//2, SCREEN_HEIGHT//2))
        elif state == "HIGH_SCORES":
            txt = big_f.render("LEADERBOARD", True, YELLOW)
            screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 120))
            for i, s in enumerate(load_scores()):
                entry = font.render(f"{i+1}. {s['name']} - {s['score']}", True, WHITE)
                screen.blit(entry, (SCREEN_WIDTH//2 - 150, 300 + i * 60))
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
