import pygame
import sys
import random
import math
import asyncio
import platform

# --- INITIALIZE ---
pygame.init()
pygame.mixer.init()

# --- SETTINGS ---
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("City Battle Royale")

clock = pygame.time.Clock()
FPS = 60
font = pygame.font.SysFont("Arial", 24, bold=True)

# --- GLOBALS ---
current_level = 1
TOTAL_LIMIT = 30
ENEMY_SPEED = 2.5
ENEMY_HEALTH_MAX = 40
player_speed = 5  # Initialized globally

# --- ASSET LOADER ---
def get_image(path, fallback_color, size=(64, 64)):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, size)
    except:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(surf, fallback_color, (size[0] // 2, size[1] // 2), size[0] // 2)
        return surf

# --- ASSET LOADER (Updated Paths) ---
player_img = get_image("src/mygame/player.png", (0, 255, 0))
enemy_imgs = [
    get_image("src/mygame/human1.png", (255, 50, 50)), 
    get_image("human2.png", (200, 0, 0)) # Agar ye file bhi folder mein hai toh yahan bhi src/mygame/ lagayein
]

# Map loading section mein bhi rasta badlein:
try:
    map_tile = pygame.image.load("src/mygame/map.png").convert()
    TILE_W, TILE_H = map_tile.get_size()
except:
    TILE_W, TILE_H = 1200, 1200
    map_tile = pygame.Surface((TILE_W, TILE_H))
    map_tile.fill((120, 120, 120))

# --- STATE VARIABLES ---
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
    except: return True

def draw_health_bar(x, y, hp, max_hp, color):
    bar_width, bar_height = 50, 5
    ratio = max(0, hp / max_hp)
    pygame.draw.rect(screen, (40, 0, 0), (x - 25, y, bar_width, bar_height))
    pygame.draw.rect(screen, color, (x - 25, y, int(bar_width * ratio), bar_height))

def drop_powerup(x, y):
    if random.random() < 0.4:
        p_type = random.choice(["health", "speed"])
        color = (0, 255, 0) if p_type == "health" else (0, 0, 255)
        powerups.append({"x": x, "y": y, "type": p_type, "color": color})

def draw_controls(screen):
    if platform.system().lower() != "android": return {}
    btns = {}
    btn_size = 80
    alpha_surf = pygame.Surface((btn_size, btn_size), pygame.SRCALPHA)
    pygame.draw.circle(alpha_surf, (200, 200, 200, 100), (40, 40), 40)

    btns['up'] = screen.blit(alpha_surf, (100, HEIGHT - 220))
    btns['down'] = screen.blit(alpha_surf, (100, HEIGHT - 90))
    btns['left'] = screen.blit(alpha_surf, (20, HEIGHT - 155))
    btns['right'] = screen.blit(alpha_surf, (180, HEIGHT - 155))
    btns['restart'] = screen.blit(alpha_surf, (WIDTH - 100, 20))
    
    screen.blit(font.render("R", True, (0,0,0)), (WIDTH - 80, 45))
    return btns

def reset_game(full_restart=False):
    global player_world_x, player_world_y, player_health, score, spawned_so_far
    global enemies, bullets, powerups, game_over, current_level, TOTAL_LIMIT, ENEMY_SPEED, ENEMY_HEALTH_MAX, player_speed
    
    if full_restart:
        current_level, TOTAL_LIMIT, ENEMY_SPEED, ENEMY_HEALTH_MAX, player_speed = 1, 30, 2.5, 40, 5
    
    player_world_x, player_world_y = TILE_W//2, TILE_H//2
    player_health, score, spawned_so_far = 100, 0, 0
    enemies, bullets, powerups, game_over = [], [], [], False

def get_closest_target(sx, sy, sid=None):
    targets = [{"x": player_world_x, "y": player_world_y}] if sid is not None else []
    for e in enemies:
        if id(e) != sid: targets.append({"x": e["x"], "y": e["y"]})
    return min(targets, key=lambda t: math.hypot(t["x"] - sx, t["y"] - sy)) if targets else None

async def main():
    global player_world_x, player_world_y, player_health, score, spawned_so_far, player_speed
    global enemies, bullets, game_over, current_level, TOTAL_LIMIT, ENEMY_SPEED, ENEMY_HEALTH_MAX, collision_on

    reset_game(True)
    spawn_timer, fire_timer = 0, 0
    touch_keys = {'up': False, 'down': False, 'left': False, 'right': False}

    while True:
        dt = clock.tick(FPS)
        screen.fill((0, 0, 0))
        control_btns = draw_controls(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r: reset_game(True)
                if event.key == pygame.K_c: collision_on = not collision_on

            if event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                is_down = (event.type == pygame.MOUSEBUTTONDOWN)
                pos = event.pos
                if control_btns:
                    if control_btns['up'].collidepoint(pos): touch_keys['up'] = is_down
                    if control_btns['down'].collidepoint(pos): touch_keys['down'] = is_down
                    if control_btns['left'].collidepoint(pos): touch_keys['left'] = is_down
                    if control_btns['right'].collidepoint(pos): touch_keys['right'] = is_down
                    if is_down and control_btns['restart'].collidepoint(pos): reset_game(True)

        if not game_over:
            spawn_timer += dt
            fire_timer += dt

            # Level Up
            if score >= TOTAL_LIMIT:
                current_level += 1
                TOTAL_LIMIT += 20; ENEMY_SPEED += 0.3; ENEMY_HEALTH_MAX += 10
                reset_game(False)

            # Movement Logic
            keys = pygame.key.get_pressed()
            vx, vy = 0, 0
            if keys[pygame.K_w] or touch_keys['up']: vy = -player_speed
            if keys[pygame.K_s] or touch_keys['down']: vy = player_speed
            if keys[pygame.K_a] or touch_keys['left']: vx = -player_speed
            if keys[pygame.K_d] or touch_keys['right']: vx = player_speed
            
            if is_walkable(player_world_x + vx, player_world_y): player_world_x += vx
            if is_walkable(player_world_x, player_world_y + vy): player_world_y += vy

            # Spawning
            if spawn_timer > 1500 and spawned_so_far < TOTAL_LIMIT:
                ex, ey = player_world_x + random.randint(-400, 400), player_world_y + random.randint(-400, 400)
                if is_walkable(ex, ey):
                    enemies.append({"x": ex, "y": ey, "health": ENEMY_HEALTH_MAX, "img": random.choice(enemy_imgs)})
                    spawned_so_far += 1
                spawn_timer = 0

            # Fire
            if fire_timer > 500:
                t = get_closest_target(player_world_x, player_world_y)
                if t and math.hypot(t["x"] - player_world_x, t["y"] - player_world_y) < 400:
                    bullets.append({"x": player_world_x, "y": player_world_y, "tx": t["x"], "ty": t["y"], "owner": "player"})
                fire_timer = 0

        # Rendering & Updates
        cam_x, cam_y = WIDTH//2 - player_world_x, HEIGHT//2 - player_world_y
        screen.blit(map_tile, (cam_x, cam_y))

        for p in powerups[:]:
            pygame.draw.circle(screen, p["color"], (int(p["x"] + cam_x), int(p["y"] + cam_y)), 10)
            if math.hypot(p["x"] - player_world_x, p["y"] - player_world_y) < 40:
                if p["type"] == "health": player_health = min(100, player_health + 30)
                else: player_speed += 1
                powerups.remove(p)

        for e in enemies[:]:
            t = get_closest_target(e["x"], e["y"], id(e))
            if t and not game_over:
                dx, dy = t["x"] - e["x"], t["y"] - e["y"]
                dist = math.hypot(dx, dy) or 1
                if dist > 60:
                    e["x"] += (dx/dist) * ENEMY_SPEED
                    e["y"] += (dy/dist) * ENEMY_SPEED
            screen.blit(e["img"], (e["x"] + cam_x - 32, e["y"] + cam_y - 32))
            draw_health_bar(e["x"] + cam_x, e["y"] + cam_y - 45, e["health"], ENEMY_HEALTH_MAX, (255, 0, 0))
            if e["health"] <= 0:
                drop_powerup(e["x"], e["y"])
                enemies.remove(e); score += 1

        for b in bullets[:]:
            dx, dy = b["tx"] - b["x"], b["ty"] - b["y"]
            dist = math.hypot(dx, dy) or 1
            b["x"] += (dx/dist) * 12; b["y"] += (dy/dist) * 12
            pygame.draw.circle(screen, (255, 255, 0), (int(b["x"] + cam_x), int(b["y"] + cam_y)), 5)
            
            if b["owner"] == "player":
                for e in enemies:
                    if math.hypot(b["x"] - e["x"], b["y"] - e["y"]) < 35:
                        e["health"] -= 15; bullets.remove(b); break
            
            if b in bullets and not (0 < b["x"] + cam_x < WIDTH and 0 < b["y"] + cam_y < HEIGHT):
                bullets.remove(b)

        if player_health > 0:
            screen.blit(player_img, (WIDTH // 2 - 32, HEIGHT // 2 - 32))
            draw_health_bar(WIDTH // 2, HEIGHT // 2 - 45, player_health, 100, (0, 255, 0))
        else: game_over = True

        screen.blit(font.render(f"LVL: {current_level}  KILLS: {score}/{TOTAL_LIMIT}", True, (255,255,255)), (20, 20))
        if game_over:
            screen.blit(font.render("GAME OVER - Press R to Restart", True, (255,0,0)), (WIDTH//2 - 150, HEIGHT//2))

        pygame.display.flip()
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())

