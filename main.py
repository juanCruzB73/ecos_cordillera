import pygame
import sys
import os
import math
import random

# Initialize pygame
pygame.init()
pygame.mixer.init()

# ==============================================================================
# GAME CONSTANTS & CONFIGURATION
# ==============================================================================
TILE_SIZE = 64
HUD_HEIGHT = 80
FPS = 60

# Palette - HSL-tailored premium colors mapped to RGB
COLOR_BG = (10, 14, 26)         # Deep Navy Space
COLOR_HUD_BG = (6, 8, 16)       # Darker Navy
COLOR_CYAN = (0, 255, 200)      # Glowing Teal/Cyan
COLOR_ORANGE = (255, 110, 0)    # Alert Orange
COLOR_GREEN = (0, 255, 120)     # Success Green
COLOR_RED = (255, 50, 50)       # Critical Red
COLOR_WHITE = (230, 235, 245)   # Clean White
COLOR_GRAY = (100, 110, 130)    # Muted Gray
COLOR_YELLOW = (255, 215, 0)    # Warning/Interactive Yellow

# Load fonts safely
def get_font(size, bold=False):
    fonts = ["Consolas", "Courier New", "Lucida Console", "monospace"]
    for f in fonts:
        try:
            return pygame.font.SysFont(f, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)

# ==============================================================================
# PARTICLE EFFECT SYSTEM
# ==============================================================================
# The Particle class handles transient aesthetic visual effects such as player 
# walking dust, active drone exhaust engine heat, portal energy, and death explosions.
class Particle:
    def __init__(self, x, y, color, speed_x, speed_y, size, life):
        self.x = x
        self.y = y
        self.color = color
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.size = size
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.life -= 1
        self.size = max(1.0, self.size * 0.96)

    def draw(self, surface, offset_x=0, offset_y=0):
        alpha = int((self.life / self.max_life) * 255)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        color_with_alpha = self.color + (alpha,)
        pygame.draw.circle(s, color_with_alpha, (self.size, self.size), self.size)
        surface.blit(s, (int(self.x + offset_x - self.size), int(self.y + offset_y - self.size)))

# ==============================================================================
# PLAYER (ALMA) ENTITY & PHYSICS
# ==============================================================================
# The Player class implements standard platformer physics, including movement,
# jumping, gravity, and Axis-Aligned Bounding Box (AABB) collision resolution.
class Player:
    def __init__(self, x, y):
        # Hitbox dimensions (slightly narrower than TILE_SIZE to feel fair)
        self.width = 36
        self.height = 52
        
        # Pixel coordinates (aligned to bottom of start tile)
        self.px = x * TILE_SIZE + (TILE_SIZE - self.width) // 2
        self.py = y * TILE_SIZE + (TILE_SIZE - self.height)
        
        # Velocity vectors
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        
        # Physics tuning parameters
        self.gravity = 0.6
        self.terminal_velocity = 12.0
        self.walk_speed = 5.0
        self.jump_force = -14.0

    def get_rect(self):
        return pygame.Rect(self.px, self.py, self.width, self.height)

    def update(self, game):
        # 1. Apply gravity if in the air
        if not self.on_ground:
            self.vy += self.gravity
            if self.vy > self.terminal_velocity:
                self.vy = self.terminal_velocity
        else:
            self.vy = max(0.0, self.vy) # Reset vertical downward velocity on landing

        # 2. Horizontal Movement and Collision Resolution
        self.px += self.vx
        rect = self.get_rect()
        # Look for collisions with solid wall tiles (#)
        for tile in game.get_solid_rects():
            if rect.colliderect(tile):
                if self.vx > 0: # Colliding on the right
                    self.px = tile.left - self.width
                elif self.vx < 0: # Colliding on the left
                    self.px = tile.right
                self.vx = 0.0  # Halt horizontal momentum
                rect = self.get_rect()

        # 3. Vertical Movement and Collision Resolution
        self.on_ground = False
        self.py += self.vy
        rect = self.get_rect()
        # Look for collisions with solid ceiling/floor tiles (#)
        for tile in game.get_solid_rects():
            if rect.colliderect(tile):
                if self.vy > 0: # Falling onto a surface
                    self.py = tile.top - self.height
                    self.on_ground = True
                    self.vy = 0.0  # Halt downward momentum
                elif self.vy < 0: # Bumping into a ceiling
                    self.py = tile.bottom
                    self.vy = 0.0  # Halt upward momentum
                rect = self.get_rect()

        # Emit dust particles while walking
        if self.on_ground and abs(self.vx) > 0 and random.random() < 0.2:
            game.particles.append(Particle(
                self.px + self.width // 2,
                self.py + self.height,
                (180, 180, 200),
                random.uniform(-1.0, 1.0) - (self.vx * 0.1),
                random.uniform(-1.0, 0.0),
                random.uniform(2, 4),
                random.randint(10, 20)
            ))

    def jump(self):
        if self.on_ground:
            self.vy = self.jump_force
            self.on_ground = False

    def draw(self, game, ox, oy):
        rect = self.get_rect().move(ox, oy)
        if game.assets.get("alma"):
            game.screen.blit(game.assets["alma"], (rect.x - (TILE_SIZE - self.width)//2, rect.y - (TILE_SIZE - self.height)))
        else:
            # Fallback player vector
            pygame.draw.rect(game.screen, COLOR_CYAN, rect, border_radius=6)
            pygame.draw.circle(game.screen, COLOR_WHITE, (rect.centerx, rect.y + 15), 8)

# ==============================================================================
# SECURITY DRONE ENTITY (ENEMY)
# ==============================================================================
# The Drone patrols back and forth horizontally. It turns around when it runs
# into a solid wall (#) OR when it reaches the edge of its current platform.
class Drone:
    def __init__(self, x, y):
        self.width = 40
        self.height = 40
        self.px = x * TILE_SIZE + (TILE_SIZE - self.width) // 2
        self.py = y * TILE_SIZE + (TILE_SIZE - self.height)
        self.vx = 2.0  # Horizontal speed
        self.dir = 1   # Direction indicator: 1 = Right, -1 = Left
        
    def get_rect(self):
        return pygame.Rect(self.px, self.py, self.width, self.height)

    def update(self, game):
        # Move drone by speed and current direction
        self.px += self.vx * self.dir
        
        # A. Check if the drone collided with a solid wall block (#)
        rect = self.get_rect()
        hit_wall = False
        for tile in game.get_solid_rects():
            if rect.colliderect(tile):
                hit_wall = True
                break
                
        # B. Check if the drone is about to run off the edge of its platform
        # Look offset depends on whether drone is moving left or right
        look_offset = self.width if self.dir > 0 else -TILE_SIZE // 2
        test_x = self.px + look_offset
        test_y = self.py + self.height + 4
        
        # Test if a platform block exists directly below the look-ahead point
        test_point = pygame.Rect(test_x, test_y, 4, 4)
        has_ground = False
        for tile in game.get_solid_rects():
            if test_point.colliderect(tile):
                has_ground = True
                break
                
        # Turn around if the drone hits a wall or has no ground to walk on
        if hit_wall or not has_ground:
            self.dir *= -1
            # Push back slightly into boundaries to prevent turn loops
            self.px += self.vx * self.dir

        # Engine exhaust particles
        if random.random() < 0.1:
            game.particles.append(Particle(
                self.px + self.width // 2,
                self.py + self.height - 5,
                COLOR_ORANGE,
                random.uniform(-0.5, 0.5) - (self.vx * self.dir * 0.1),
                random.uniform(0.5, 1.5),
                random.uniform(1.5, 3),
                random.randint(10, 20)
            ))

    def draw(self, game, ox, oy):
        rect = self.get_rect().move(ox, oy)
        if game.assets.get("drone"):
            game.screen.blit(game.assets["drone"], (rect.x - (TILE_SIZE - self.width)//2, rect.y - (TILE_SIZE - self.height)//2))
        else:
            # Fallback drone shape
            pygame.draw.rect(game.screen, COLOR_ORANGE, rect, border_radius=4)
            pygame.draw.circle(game.screen, COLOR_RED, rect.center, 5)

        # Pulse engine glow
        glow_pulse = int(140 + 115 * math.sin(pygame.time.get_ticks() * 0.015))
        s = pygame.Surface((20, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (COLOR_ORANGE[0], COLOR_ORANGE[1], COLOR_ORANGE[2], glow_pulse), (0, 0, 20, 8))
        game.screen.blit(s, (rect.centerx - 10, rect.bottom - 4))

# ==============================================================================
# POWER GENERATOR OBJECT (CHECKPOINT)
# ==============================================================================
# The Generator must be activated by the player pressing [E] when standing near.
# Activating the generator unlocks the exit door portal.
class Generator:
    def __init__(self, x, y):
        self.grid_x = x
        self.grid_y = y
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.activated = False

    def draw(self, game, ox, oy):
        draw_rect = self.rect.move(ox, oy)
        if game.assets.get("generator"):
            self.screen.blit(game.assets["generator"], draw_rect.topleft)
        else:
            # Fallback generator UI representation
            pygame.draw.rect(game.screen, (40, 50, 70), draw_rect)
            pygame.draw.rect(game.screen, COLOR_GRAY, draw_rect, 2)
            
        # Glowing indicator light (Red = Inactive, Green = Active)
        light_color = COLOR_GREEN if self.activated else COLOR_RED
        pulse = int(170 + 85 * math.sin(pygame.time.get_ticks() * 0.01))
        
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(s, light_color + (pulse,), (8, 8), 8)
        game.screen.blit(s, (draw_rect.centerx - 8, draw_rect.centery - 12))

# ==============================================================================
# MAIN GAME CLASS (ENGINE, STATE MANAGEMENT, EVENT LOOP)
# ==============================================================================
class Game:
    def __init__(self):
        self.level_data = []
        self.grid_w = 0
        self.grid_h = 0
        self.load_level("levels/level1.txt")
        
        # Setup Pygame screen size and window caption
        self.win_w = self.grid_w * TILE_SIZE
        self.win_h = self.grid_h * TILE_SIZE + HUD_HEIGHT
        self.screen = pygame.display.set_mode((self.win_w, self.win_h))
        pygame.display.set_caption("Ecos Cordillera - Operation Alma Platformer")
        self.clock = pygame.time.Clock()
        
        self.load_assets()
        
        # Tuning State variables
        self.current_frequency = 88.5
        self.target_frequency = 104.5
        self.freq_connected = False
        
        self.state = "START"  # START, PLAYING, TUNING, WON, GAME_OVER
        self.particles = []
        self.shake_intensity = 0
        self.shake_decay = 0.9
        self.shake_x = 0
        self.shake_y = 0
        
        self.steps = 0  # Serves as Jump/Action counter
        self.start_time = 0
        self.elapsed_time = 0
        self.near_generator_msg = False
        
        self.reset_game()

    def load_level(self, filename):
        if not os.path.exists(filename):
            self.level_data = [
                "####################",
                "#..................#",
                "#............G.....#",
                "#..........#####...#",
                "#..................#",
                "#......#####.......#",
                "#..D...............#",
                "#.#####..........E.#",
                "#..............#####",
                "#........#####.....#",
                "#P.................#",
                "####################"
            ]
        else:
            with open(filename, "r") as f:
                self.level_data = [line.strip() for line in f.readlines() if line.strip()]
        
        self.grid_h = len(self.level_data)
        self.grid_w = len(self.level_data[0]) if self.grid_h > 0 else 0

    def load_assets(self):
        self.assets = {}
        paths = {
            "floor": "assets/floor.png",
            "wall": "assets/wall.png",
            "door": "assets/door.png",
            "alma": "assets/alma.png",
            "drone": "assets/drone.png",
            "generator": "assets/generator.png"
        }
        for key, path in paths.items():
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    self.assets[key] = img
                except Exception as e:
                    print(f"Error loading {path}: {e}")
                    self.assets[key] = None
            else:
                self.assets[key] = None

    def reset_game(self):
        self.start_time = pygame.time.get_ticks()
        self.particles.clear()
        self.shake_intensity = 0
        self.steps = 0
        self.current_frequency = 88.5
        self.freq_connected = False
        self.near_generator_msg = False
        
        self.drones = []
        self.solids = []
        self.player = None
        self.generator = None
        self.door_rect = None

        for r in range(self.grid_h):
            for c in range(self.grid_w):
                ch = self.level_data[r][c]
                rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if ch == '#':
                    self.solids.append(rect)
                elif ch == 'P':
                    self.player = Player(c, r)
                elif ch == 'G':
                    self.generator = Generator(c, r)
                elif ch == 'E':
                    self.door_rect = rect
                elif ch == 'D':
                    self.drones.append(Drone(c, r))

    def get_solid_rects(self):
        return self.solids

    def trigger_shake(self, intensity):
        self.shake_intensity = intensity

    def add_explosion(self, x, y, color):
        for _ in range(35):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 6.0)
            sx = math.cos(angle) * speed
            sy = math.sin(angle) * speed
            size = random.uniform(3, 7)
            life = random.randint(20, 45)
            self.particles.append(Particle(x, y, color, sx, sy, size, life))

    def update(self):
        # Update screen shake
        if self.shake_intensity > 0.5:
            self.shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= self.shake_decay
        else:
            self.shake_x = 0
            self.shake_y = 0

        # Handle State updates
        if self.state == "PLAYING":
            self.elapsed_time = (pygame.time.get_ticks() - self.start_time) // 1000
            
            # Update player
            self.player.update(self)

            # Update drones
            for d in self.drones:
                d.update(self)

            # Check generator proximity
            self.near_generator_msg = False
            if self.generator and not self.generator.activated:
                p_center = self.player.get_rect().center
                g_center = self.generator.rect.center
                if math.hypot(p_center[0] - g_center[0], p_center[1] - g_center[1]) < TILE_SIZE * 1.3:
                    self.near_generator_msg = True

            # Drone collisions
            p_rect = self.player.get_rect()
            for d in self.drones:
                if p_rect.colliderect(d.get_rect()):
                    self.state = "GAME_OVER"
                    self.add_explosion(p_rect.centerx, p_rect.centery, COLOR_RED)
                    self.trigger_shake(16)
                    break

            # Door collision
            if self.door_rect and p_rect.colliderect(self.door_rect):
                if self.generator and self.generator.activated:
                    # Enter tuning state!
                    self.state = "TUNING"
                else:
                    # Warning: Need generator
                    if random.random() < 0.1:
                        # Draw warning sparks at the door
                        self.add_explosion(self.door_rect.centerx, self.door_rect.centery, COLOR_ORANGE)

            # Boundaries check (fell off map)
            if self.player.py > self.grid_h * TILE_SIZE:
                self.state = "GAME_OVER"
                self.trigger_shake(10)

            # Portal floating glow
            if self.door_rect and random.random() < 0.2:
                door_center = self.door_rect.center
                color = COLOR_CYAN if (self.generator and self.generator.activated) else COLOR_RED
                self.particles.append(Particle(
                    door_center[0] + random.uniform(-20, 20),
                    door_center[1] + random.uniform(-20, 20),
                    color,
                    random.uniform(-0.5, 0.5),
                    random.uniform(-1.0, -0.2),
                    random.uniform(2, 4),
                    random.randint(15, 30)
                ))

        elif self.state == "TUNING":
            # Check connection matches exactly 104.5 MHz
            self.freq_connected = abs(self.current_frequency - self.target_frequency) < 0.01
            # Portal sparks on connection
            if self.freq_connected and random.random() < 0.4:
                door_center = self.door_rect.center
                self.particles.append(Particle(
                    door_center[0] + random.uniform(-25, 25),
                    door_center[1] + random.uniform(-25, 25),
                    COLOR_GREEN,
                    random.uniform(-1, 1),
                    random.uniform(-1, 1),
                    random.uniform(2.5, 5),
                    random.randint(20, 40)
                ))

        # Update particles
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw_background(self):
        # Draw background grids/tiles
        for r in range(self.grid_h):
            for c in range(self.grid_w):
                x = c * TILE_SIZE + self.shake_x
                y = r * TILE_SIZE + self.shake_y
                if self.assets.get("floor"):
                    # Render background floor tinted dark
                    self.screen.blit(self.assets["floor"], (x, y))
                else:
                    # Fallback simple dark floor
                    rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(self.screen, (15, 20, 35), rect)
                    pygame.draw.rect(self.screen, (18, 24, 42), rect, 1)

        # Draw darkened overlay for background tiles
        bg_overlay = pygame.Surface((self.win_w, self.grid_h * TILE_SIZE))
        bg_overlay.fill((8, 10, 24))
        bg_overlay.set_alpha(190)
        self.screen.blit(bg_overlay, (0, 0))

    def draw(self):
        self.screen.fill(COLOR_BG)
        
        ox = self.shake_x
        oy = self.shake_y

        if self.state in ["PLAYING", "TUNING", "WON", "GAME_OVER"]:
            self.draw_background()

            # Draw static solid tiles
            for block in self.solids:
                draw_rect = block.move(ox, oy)
                if self.assets.get("wall"):
                    self.screen.blit(self.assets["wall"], draw_rect.topleft)
                else:
                    pygame.draw.rect(self.screen, (32, 40, 58), draw_rect)
                    pygame.draw.rect(self.screen, (45, 55, 78), draw_rect, 2)

            # Draw Generator
            if self.generator:
                self.generator.draw(self, ox, oy)

            # Draw Exit Door
            if self.door_rect:
                draw_rect = self.door_rect.move(ox, oy)
                if self.assets.get("door"):
                    self.screen.blit(self.assets["door"], draw_rect.topleft)
                else:
                    door_color = COLOR_CYAN if (self.generator and self.generator.activated) else COLOR_RED
                    pygame.draw.rect(self.screen, door_color, draw_rect, border_radius=4)
                    pygame.draw.rect(self.screen, COLOR_BG, draw_rect.inflate(-16, -16), border_radius=4)

            # Draw Drones
            for d in self.drones:
                d.draw(self, ox, oy)

            # Draw Player (if alive)
            if self.state != "GAME_OVER" and self.player:
                self.player.draw(self, ox, oy)

            # Draw Particles
            for p in self.particles:
                p.draw(self.screen, ox, oy)

            # Draw HUD
            self.draw_hud()

        # Overlays
        if self.state == "START":
            self.draw_start_screen()
        elif self.state == "TUNING":
            self.draw_tuning_screen()
        elif self.state == "WON":
            self.draw_win_screen()
        elif self.state == "GAME_OVER":
            self.draw_game_over_screen()

        pygame.display.flip()

    def draw_hud(self):
        hud_rect = pygame.Rect(0, self.grid_h * TILE_SIZE, self.win_w, HUD_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, hud_rect)
        pygame.draw.line(self.screen, COLOR_GRAY, (0, hud_rect.top), (self.win_w, hud_rect.top), 2)
        
        font = get_font(24)
        lbl_jumps = font.render(f"JUMPS: {self.steps}", True, COLOR_WHITE)
        lbl_time = font.render(f"TIME: {self.elapsed_time}s", True, COLOR_WHITE)
        
        status_text = "DOOR LOCKED: ACTIVATE GENERATOR"
        status_color = COLOR_RED
        if self.generator and self.generator.activated:
            status_text = "GENERATOR ACTIVE: PROCEED TO PORTAL"
            status_color = COLOR_CYAN
            
        lbl_status = font.render(status_text, True, status_color)
        
        self.screen.blit(lbl_status, (20, hud_rect.top + 15))
        self.screen.blit(lbl_jumps, (self.win_w - 300, hud_rect.top + 15))
        self.screen.blit(lbl_time, (self.win_w - 140, hud_rect.top + 15))
        
        # Interactions tips
        font_sub = get_font(18)
        if self.near_generator_msg:
            lbl_tip = font_sub.render(">> PRESS [E] TO ACTIVATE POWER GENERATOR <<", True, COLOR_YELLOW)
        else:
            lbl_tip = font_sub.render("Controls: A/D/Arrows = Move | W/Space/Up = Jump", True, COLOR_GRAY)
        self.screen.blit(lbl_tip, (20, hud_rect.top + 45))

    def draw_start_screen(self):
        overlay = pygame.Surface((self.win_w, self.win_h))
        overlay.fill((8, 10, 20))
        self.screen.blit(overlay, (0, 0))
        
        # Design lines
        pygame.draw.line(self.screen, COLOR_CYAN, (60, 100), (self.win_w - 60, 100), 2)
        pygame.draw.line(self.screen, COLOR_CYAN, (60, self.win_h - 120), (self.win_w - 60, self.win_h - 120), 2)
        
        font_title = get_font(56, bold=True)
        lbl_title = font_title.render("ECOS CORDILLERA", True, COLOR_WHITE)
        lbl_title_shadow = font_title.render("ECOS CORDILLERA", True, COLOR_CYAN)
        
        pulse = int(127 + 128 * math.sin(pygame.time.get_ticks() * 0.005))
        lbl_start = get_font(24).render("PRESS SPACE TO BEGIN OPERATIONS", True, (pulse, pulse, pulse))
        
        font_desc = get_font(20)
        desc_lines = [
            "Operator: ALMA",
            "Environment: High Mountain Platform Station",
            "Mission Instructions:",
            "  1. Climb platforms and dodge security drones.",
            "  2. Find and activate the POWER GENERATOR [E].",
            "  3. Reach the GATE PORTAL [E] and tune the frequency to 104.5 MHz."
        ]
        
        self.screen.blit(lbl_title_shadow, (self.win_w//2 - lbl_title.get_width()//2 + 2, 142))
        self.screen.blit(lbl_title, (self.win_w//2 - lbl_title.get_width()//2, 140))
        
        y_offset = 240
        for line in desc_lines:
            color = COLOR_YELLOW if "GENERATOR" in line or "104.5" in line else COLOR_WHITE
            if "Mission Instructions" in line: color = COLOR_CYAN
            txt = font_desc.render(line, True, color)
            self.screen.blit(txt, (self.win_w//2 - txt.get_width()//2, y_offset))
            y_offset += 32
            
        self.screen.blit(lbl_start, (self.win_w//2 - lbl_start.get_width()//2, self.win_h - 180))

    def draw_tuning_screen(self):
        # Semi-transparent dark blue overlay
        overlay = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        overlay.fill((5, 10, 25, 230))
        self.screen.blit(overlay, (0, 0))
        
        # Center box
        box_w, box_h = 560, 360
        box_rect = pygame.Rect(self.win_w//2 - box_w//2, self.win_h//2 - box_h//2 - 20, box_w, box_h)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, box_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_CYAN, box_rect, 2, border_radius=10)
        
        font_title = get_font(32, bold=True)
        lbl_head = font_title.render("ANTENNA LINK TUNER", True, COLOR_CYAN)
        self.screen.blit(lbl_head, (box_rect.centerx - lbl_head.get_width()//2, box_rect.top + 25))
        
        # Draw Frequency display
        font_freq = get_font(52, bold=True)
        freq_str = f"{self.current_frequency:.1f} MHz"
        lbl_freq = font_freq.render(freq_str, True, COLOR_GREEN if self.freq_connected else COLOR_ORANGE)
        self.screen.blit(lbl_freq, (box_rect.centerx - lbl_freq.get_width()//2, box_rect.top + 90))
        
        # Target details
        font_detail = get_font(22)
        lbl_target = font_detail.render(f"Target Frequency: {self.target_frequency} MHz", True, COLOR_WHITE)
        self.screen.blit(lbl_target, (box_rect.centerx - lbl_target.get_width()//2, box_rect.top + 160))
        
        # Tuner slider visual
        slider_y = box_rect.top + 210
        pygame.draw.line(self.screen, COLOR_GRAY, (box_rect.left + 50, slider_y), (box_rect.right - 50, slider_y), 4)
        
        # Map current frequency ratio to slider position
        min_f, max_f = 88.0, 108.0
        ratio = (self.current_frequency - min_f) / (max_f - min_f)
        ratio = max(0.0, min(1.0, ratio))
        slider_x = int(box_rect.left + 50 + ratio * (box_w - 100))
        
        # Target marker on slider
        target_ratio = (self.target_frequency - min_f) / (max_f - min_f)
        target_x = int(box_rect.left + 50 + target_ratio * (box_w - 100))
        pygame.draw.circle(self.screen, COLOR_CYAN, (target_x, slider_y), 6)
        
        # Slider handle
        pygame.draw.rect(self.screen, COLOR_WHITE, (slider_x - 6, slider_y - 15, 12, 30), border_radius=3)
        
        # Oscilloscope visual effect in the center box
        wave_surface = pygame.Surface((box_w - 80, 50), pygame.SRCALPHA)
        wave_pts = []
        freq_diff = abs(self.current_frequency - self.target_frequency)
        wave_speed = pygame.time.get_ticks() * 0.02
        amplitude = max(2.0, 20.0 - freq_diff * 4.0)
        frequency_mod = 0.05 + (0.2 / max(0.1, freq_diff))
        
        for wx in range(box_w - 80):
            wy = 25 + amplitude * math.sin(wx * frequency_mod + wave_speed)
            wave_pts.append((wx, int(wy)))
            
        if len(wave_pts) > 1:
            color = COLOR_GREEN if self.freq_connected else COLOR_CYAN
            pygame.draw.lines(wave_surface, color, False, wave_pts, 2)
        self.screen.blit(wave_surface, (box_rect.left + 40, box_rect.top + 250))
        
        # Action prompts
        font_prompt = get_font(20)
        if self.freq_connected:
            pulse = int(127 + 128 * math.sin(pygame.time.get_ticks() * 0.007))
            lbl_act = font_prompt.render("CONNECTION LOCKED! PRESS SPACE TO ESCAPE", True, (pulse, 255, pulse))
        else:
            lbl_act = font_prompt.render("Press 'Q' to TUNE DOWN  |  'E' to TUNE UP", True, COLOR_WHITE)
            
        self.screen.blit(lbl_act, (box_rect.centerx - lbl_act.get_width()//2, box_rect.bottom - 40))

    def draw_win_screen(self):
        overlay = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        overlay.fill((0, 24, 15, 210))
        self.screen.blit(overlay, (0, 0))
        
        font_title = get_font(52, bold=True)
        lbl_win = font_title.render("MISSION COMPLETED", True, COLOR_GREEN)
        
        font_stats = get_font(26)
        lbl_stats1 = font_stats.render(f"Frequencies Synced: {self.target_frequency} MHz", True, COLOR_WHITE)
        lbl_stats2 = font_stats.render(f"Total Steps/Jumps: {self.steps}", True, COLOR_WHITE)
        lbl_stats3 = font_stats.render(f"Time Taken: {self.elapsed_time}s", True, COLOR_WHITE)
        
        pulse = int(127 + 128 * math.sin(pygame.time.get_ticks() * 0.006))
        lbl_restart = get_font(22).render("PRESS SPACE TO RETURN TO ORBIT (REPLAY)", True, (pulse, 255, pulse))
        
        self.screen.blit(lbl_win, (self.win_w//2 - lbl_win.get_width()//2, self.win_h//2 - 120))
        self.screen.blit(lbl_stats1, (self.win_w//2 - lbl_stats1.get_width()//2, self.win_h//2 - 30))
        self.screen.blit(lbl_stats2, (self.win_w//2 - lbl_stats2.get_width()//2, self.win_h//2 + 10))
        self.screen.blit(lbl_stats3, (self.win_w//2 - lbl_stats3.get_width()//2, self.win_h//2 + 50))
        self.screen.blit(lbl_restart, (self.win_w//2 - lbl_restart.get_width()//2, self.win_h//2 + 120))

    def draw_game_over_screen(self):
        overlay = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        overlay.fill((30, 4, 4, 225))
        self.screen.blit(overlay, (0, 0))
        
        font_title = get_font(52, bold=True)
        lbl_fail = font_title.render("CONNECTION TERMINATED", True, COLOR_RED)
        
        font_stats = get_font(24)
        lbl_detail = font_stats.render("Alma fell or was detected by a mountain patrol drone.", True, COLOR_WHITE)
        
        pulse = int(127 + 128 * math.sin(pygame.time.get_ticks() * 0.01))
        lbl_restart = get_font(22).render("PRESS 'R' TO RESTORE PREVIOUS STATE", True, (255, pulse, pulse))
        
        self.screen.blit(lbl_fail, (self.win_w//2 - lbl_fail.get_width()//2, self.win_h//2 - 80))
        self.screen.blit(lbl_detail, (self.win_w//2 - lbl_detail.get_width()//2, self.win_h//2 + 10))
        self.screen.blit(lbl_restart, (self.win_w//2 - lbl_restart.get_width()//2, self.win_h//2 + 80))

    def run(self):
        while True:
            # Event Polling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                elif event.type == pygame.KEYDOWN:
                    if self.state == "START":
                        if event.key == pygame.K_SPACE:
                            self.state = "PLAYING"
                            self.reset_game()
                            
                    elif self.state == "PLAYING":
                        # Jump Triggers
                        if event.key in [pygame.K_w, pygame.K_UP, pygame.K_SPACE]:
                            if self.player.on_ground:
                                self.player.jump()
                                self.steps += 1
                        # Interact Generator
                        elif event.key == pygame.K_e:
                            if self.near_generator_msg and self.generator:
                                self.generator.activated = True
                                self.near_generator_msg = False
                                # Sprout particles from generator
                                g_center = self.generator.rect.center
                                self.add_explosion(g_center[0], g_center[1], COLOR_GREEN)
                                self.trigger_shake(6)
                                
                    elif self.state == "TUNING":
                        # Tune radio with Q/E
                        if event.key == pygame.K_q:
                            self.current_frequency = max(88.0, self.current_frequency - 0.2)
                        elif event.key == pygame.K_e:
                            self.current_frequency = min(108.0, self.current_frequency + 0.2)
                        elif event.key == pygame.K_SPACE:
                            if self.freq_connected:
                                self.state = "WON"
                                door_center = self.door_rect.center
                                self.add_explosion(door_center[0], door_center[1], COLOR_GREEN)
                                self.trigger_shake(12)
                                
                    elif self.state == "WON":
                        if event.key == pygame.K_SPACE:
                            self.state = "PLAYING"
                            self.reset_game()
                            
                    elif self.state == "GAME_OVER":
                        if event.key == pygame.K_r:
                            self.state = "PLAYING"
                            self.reset_game()

            # Realtime input parsing for horizontal player movement
            if self.state == "PLAYING":
                keys = pygame.key.get_pressed()
                left_pressed = keys[pygame.K_a] or keys[pygame.K_LEFT]
                right_pressed = keys[pygame.K_d] or keys[pygame.K_RIGHT]
                
                if left_pressed and not right_pressed:
                    self.player.vx = -self.player.walk_speed
                elif right_pressed and not left_pressed:
                    self.player.vx = self.player.walk_speed
                else:
                    self.player.vx = 0.0

            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
