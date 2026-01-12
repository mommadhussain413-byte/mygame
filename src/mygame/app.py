import pygame
import sys
import random
import math
import asyncio
import requests # Sabse upar check karein
import platform

# --- INITIALIZE ---
pygame.init()
pygame.mixer.init()

# --- SETTINGS ---
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("City Battle Royale - Levels & Restart")

clock = pygame.time.Clock()
FPS = 60
font = pygame.font.SysFont("Arial", 20, bold=True)

# --- GLOBALS & LEVEL SYSTEM ---
current_level = 1
TOTAL_LIMIT = 30
ENEMY_SPEED = 2.5
ENEMY_HEALTH_MAX = 40


# --- ASSET LOADER ---
def get_image(path, fallback_color, size=(64, 64)):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, size)
    except:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(surf, fallback_color, (size[0] // 2, size[1] // 2), size[0] // 2)
        return surf


# Load Map
try:
    map_tile = pygame.image.load("map.png").convert()
    TILE_W, TILE_H = map_tile.get_size()
except:
    TILE_W, TILE_H = 1200, 1200
    map_tile = pygame.Surface((TILE_W, TILE_H))
    map_tile.fill((120, 120, 120))

player_img = get_image("player.png", (0, 255, 0))
enemy_imgs = [get_image("human1.png", (255, 50, 50)), get_image("human2.png", (200, 0, 0))]

# --- GAME STATE VARIABLES ---
player_world_x, player_world_y = 0, 0
player_health = 100
score = 0
spawned_so_far = 0
enemies = []
bullets = []
powerups = []
collision_on = True
game_over = False


def is_walkable(world_x, world_y):
    if not collision_on: return True
    lx, ly = int(world_x % TILE_W), int(world_y % TILE_H)
    try:
        p = map_tile.get_at((lx, ly))
        return (p.r + p.g + p.b) / 3 > 85
    except:
        return True



def draw_health_bar(x, y, hp, max_hp, color):
    # Health bar ki lambai aur unchai (width and height)
    bar_width = 50
    bar_height = 5

    # Ye calculate karta hai ki kitni health bachi hai (0 se 1 ke beech)
    # max(0, ...) isliye taaki health minus mein na dikhe
    health_ratio = max(0, hp / max_hp)

    # 1. Background Bar (Dark Red/Brown) - Ye piche rahegi
    # (x - 25) isliye kiya hai taaki bar player/enemy ke bilkul center mein rahe
    pygame.draw.rect(screen, (40, 0, 0), (x - 25, y, bar_width, bar_height))

    # 2. Actual Health Bar (Green for Player, Red for Enemy)
    # Iski width health_ratio ke hisaab se kam ya zyada hogi
    pygame.draw.rect(screen, color, (x - 25, y, int(bar_width * health_ratio), bar_height))
def drop_powerup(x, y):
        chance = random.random()
        if chance < 0.4:  # 40% chance hai powerup milne ki
            p_type = random.choice(["health", "speed"])
            color = (0, 255, 0) if p_type == "health" else (0, 0, 255)  # Green for health, Blue for speed
            powerups.append({"x": x, "y": y, "type": p_type, "color": color})
def draw_controls(screen):
    # Sirf Android par buttons dikhane ke liye (Briefcase ise detect kar leta hai)
    # Agar aap computer par test kar rahe hain aur buttons dekhna chahte hain,
    # toh niche wali line ko temporary delete kar sakte hain.
    if platform.system().lower() != "android": return {}

    btns = {}
    btn_size = 70
    alpha_surf = pygame.Surface((btn_size, btn_size), pygame.SRCALPHA)
    pygame.draw.circle(alpha_surf, (200, 200, 200, 150), (35, 35), 35)  # Transparent circle

    # D-Pad (Left Side)
    btns['up'] = screen.blit(alpha_surf, (100, HEIGHT - 200))
    btns['down'] = screen.blit(alpha_surf, (100, HEIGHT - 80))
    btns['left'] = screen.blit(alpha_surf, (30, HEIGHT - 140))
    btns['right'] = screen.blit(alpha_surf, (170, HEIGHT - 140))

    # Action Buttons (Right Side)
    btns['pause'] = screen.blit(alpha_surf, (WIDTH - 100, 20))
    btns['restart'] = screen.blit(alpha_surf, (WIDTH - 100, 110))

    # Buttons par text likhna
    screen.blit(font.render("W", True, (0, 0, 0)), (125, HEIGHT - 185))
    screen.blit(font.render("S", True, (0, 0, 0)), (125, HEIGHT - 65))
    screen.blit(font.render("A", True, (0, 0, 0)), (55, HEIGHT - 125))
    screen.blit(font.render("D", True, (0, 0, 0)), (195, HEIGHT - 125))
    screen.blit(font.render("||", True, (0, 0, 0)), (WIDTH - 80, 40))
    screen.blit(font.render("R", True, (0, 0, 0)), (WIDTH - 80, 130))

    return btns


def find_safe_spawn():
    for _ in range(1000):
        rx, ry = random.randint(0, TILE_W - 1), random.randint(0, TILE_H - 1)
        if is_walkable(rx, ry): return rx, ry
    return 100, 100


def reset_game(full_restart=False):
    global powerups
    powerups = []
    global player_world_x, player_world_y, player_health, score, spawned_so_far
    global enemies, bullets, game_over, current_level, TOTAL_LIMIT, ENEMY_SPEED, ENEMY_HEALTH_MAX

    if full_restart:
        current_level = 1
        TOTAL_LIMIT = 30
        ENEMY_SPEED = 2.5
        ENEMY_HEALTH_MAX = 40

    player_world_x, player_world_y = find_safe_spawn()
    player_health = 100
    score = 0
    spawned_so_far = 0
    enemies = []
    bullets = []
    game_over = False


def get_closest_target(sx, sy, sid=None):
    targets = [{"x": player_world_x, "y": player_world_y, "type": "player"}] if sid is not None else []
    for e in enemies:
        if id(e) != sid: targets.append({"x": e["x"], "y": e["y"], "type": "enemy"})
    return min(targets, key=lambda t: math.hypot(t["x"] - sx, t["y"] - sy)) if targets else None


# Initial Setup
reset_game(True)


async def main():
    global player_world_x, player_world_y, player_health, score, spawned_so_far
    global enemies, bullets, game_over, current_level, TOTAL_LIMIT, ENEMY_SPEED, ENEMY_HEALTH_MAX, collision_on

    spawn_timer = 0
    fire_timer = 0

    running = True
    while running:
        dt = clock.tick(FPS)
        screen.fill((0, 0, 0))

        for event in pygame.event.get():
            # Buttons detect karne ke liye variable
            touch_keys = {'up': False, 'down': False, 'left': False, 'right': False}

            # Draw controls and get their positions
            control_btns = draw_controls(screen)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False

                # Android Touch Detection
                if event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    pos = event.pos
                    is_pressed = (event.type == pygame.MOUSEBUTTONDOWN)

                    if control_btns:
                        if control_btns['up'].collidepoint(pos): touch_keys['up'] = is_pressed
                        if control_btns['down'].collidepoint(pos): touch_keys['down'] = is_pressed
                        if control_btns['left'].collidepoint(pos): touch_keys['left'] = is_pressed
                        if control_btns['right'].collidepoint(pos): touch_keys['right'] = is_pressed

                        if is_pressed and control_btns['restart'].collidepoint(pos):
                            reset_game(True)
                        if is_pressed and control_btns['pause'].collidepoint(pos):
                            # Simple Pause Logic
                            paused = True
                            while paused:
                                for ev in pygame.event.get():
                                    if ev.type == pygame.MOUSEBUTTONDOWN and control_btns['pause'].collidepoint(ev.pos):
                                        paused = False
                                pygame.display.flip()
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c: collision_on = not collision_on
                if event.key == pygame.K_r and game_over: reset_game(True)

        if not game_over:
            spawn_timer += dt
            fire_timer += dt

            # Level Up Logic
            if score >= TOTAL_LIMIT:
                current_level += 1
                TOTAL_LIMIT *= 2
                ENEMY_SPEED += 0.5
                ENEMY_HEALTH_MAX += 10
                reset_game(False)

            # Movement
            keys = pygame.key.get_pressed()
            nx, ny = player_world_x, player_world_y
            p_speed = 5
            # Keyboard + Touch Movement
            if keys[pygame.K_w] or keys[pygame.K_UP] or touch_keys['up']: ny -= p_speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN] or touch_keys['down']: ny += p_speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT] or touch_keys['left']: nx -= p_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT] or touch_keys['right']: nx += p_speed
            if is_walkable(nx, player_world_y): player_world_x = nx
            if is_walkable(player_world_x, ny): player_world_y = ny

            # Spawn Enemies
            if spawn_timer > 1200 and spawned_so_far < TOTAL_LIMIT:
                ex, ey = player_world_x + random.randint(-500, 500), player_world_y + random.randint(-500, 500)
                if is_walkable(ex, ey):
                    enemies.append({"x": ex, "y": ey, "health": ENEMY_HEALTH_MAX, "img": random.choice(enemy_imgs)})
                    spawned_so_far += 1
                spawn_timer = 0

            # Shooting Logic
            if fire_timer > 400:
                p_t = get_closest_target(player_world_x, player_world_y)
                if p_t and math.hypot(p_t["x"] - player_world_x, p_t["y"] - player_world_y) < 450:
                    bullets.append(
                        {"x": player_world_x, "y": player_world_y, "tx": p_t["x"], "ty": p_t["y"], "owner": "player"})
                for e in enemies:
                    e_t = get_closest_target(e["x"], e["y"], id(e))
                    if e_t and math.hypot(e_t["x"] - e["x"], e_t["y"] - e["y"]) < 400:
                        bullets.append({"x": e["x"], "y": e["y"], "tx": e_t["x"], "ty": e_t["y"], "owner": "enemy"})
                fire_timer = 0

        # Draw Map
        cam_x, cam_y = WIDTH // 2 - player_world_x, HEIGHT // 2 - player_world_y
        start_x = ((-player_world_x + WIDTH // 2) % TILE_W) - TILE_W
        start_y = ((-player_world_y + HEIGHT // 2) % TILE_H) - TILE_H
        for x in range(start_x, WIDTH + TILE_W, TILE_W):
            for y in range(start_y, HEIGHT + TILE_H, TILE_H):
                screen.blit(map_tile, (x, y))

        # Update Enemies & Bullets
        for e in enemies[:]:
            t = get_closest_target(e["x"], e["y"], id(e))
            if t and not game_over:
                dx, dy = t["x"] - e["x"], t["y"] - e["y"]
                dist = math.hypot(dx, dy)
                if dist > 55:
                    nex, ney = e["x"] + (dx / dist) * ENEMY_SPEED, e["y"] + (dy / dist) * ENEMY_SPEED
                    if is_walkable(nex, e["y"]): e["x"] = nex
                    if is_walkable(e["x"], ney): e["y"] = ney
            screen.blit(e["img"], (e["x"] + cam_x - 32, e["y"] + cam_y - 32))
            # Is line ko screen.blit(e["img"]...) ke theek niche likhein
            draw_health_bar(e["x"] + cam_x, e["y"] + cam_y - 45, e["health"], ENEMY_HEALTH_MAX, (255, 0, 0))
            if e["health"] <= 0:
                drop_powerup(e["x"], e["y"])  # <-- Ye line add karein
                enemies.remove(e)
                score += 1
            enemies.remove(e)
            score += 1

        for b in bullets[:]:
            # Draw and Check Powerups
            for p in powerups[:]:
                px, py = p["x"] + cam_x, p["y"] + cam_y
                pygame.draw.circle(screen, p["color"], (int(px), int(py)), 8)  # Powerup dot

                # Player touch powerup
                if math.hypot(p["x"] - player_world_x, p["y"] - player_world_y) < 35:
                    if p["type"] == "health":
                        player_health = min(100, player_health + 20)
                    elif p["type"] == "speed":
                        player_speed += 1  # Permanent speed boost (ya aap timer laga sakte hain)
                    powerups.remove(p)
                    continue

                # Enemies touch powerup
                for e in enemies:
                    if math.hypot(p["x"] - e["x"], p["y"] - e["y"]) < 35:
                        if p["type"] == "health":
                            e["health"] = min(ENEMY_HEALTH_MAX, e["health"] + 20)
                        # Speed boost for enemy can also be added here
                        if p in powerups: powerups.remove(p)
                        break
            bdx, bdy = b["tx"] - b["x"], b["ty"] - b["y"]
            bd = math.hypot(bdx, bdy) or 1
            b["x"] += (bdx / bd) * 14
            b["y"] += (bdy / bd) * 14
            bx, by = b["x"] + cam_x, b["y"] + cam_y
            pygame.draw.circle(screen, (255, 255, 0) if b["owner"] == "player" else (255, 255, 255), (int(bx), int(by)),
                               4)

            if b["owner"] == "player":
                for e in enemies:
                    if math.hypot(b["x"] - e["x"], b["y"] - e["y"]) < 35:
                        e["health"] -= 10
                        if b in bullets: bullets.remove(b)
                        break
            elif math.hypot(b["x"] - player_world_x, b["y"] - player_world_y) < 30:
                player_health -= 4
                if b in bullets: bullets.remove(b)
            if not (0 < bx < WIDTH and 0 < by < HEIGHT) and b in bullets: bullets.remove(b)

        # Draw Player
        if player_health > 0:
            screen.blit(player_img, (WIDTH // 2 - 32, HEIGHT // 2 - 32))
            # Is line ko screen.blit(player_img...) ke theek niche likhein
            draw_health_bar(WIDTH // 2, HEIGHT // 2 - 45, player_health, 100, (0, 255, 0))
        else:
            game_over = True

        # UI
        screen.blit(font.render(f"LEVEL: {current_level}  KILLS: {score}/{TOTAL_LIMIT}", True, (255, 255, 255)),
                    (20, 20))
        if game_over:
            screen.blit(font.render("GAME OVER - Press R to Restart", True, (255, 0, 0)),
                        (WIDTH // 2 - 140, HEIGHT // 2))

        pygame.display.flip()
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
