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
COLOR_SHADOW = (12, 18, 32)     # Safe shadow cover

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
        
        # Animation state
        self.move_direction = "idle"
        self.facing = "right"
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 8

        # Input forgiveness keeps jumps responsive even if the key press lands
        # a few frames before or after the exact ground-contact frame.
        self.jump_buffer_frames = 8
        self.coyote_frames = 6
        self.jump_buffer_timer = 0
        self.coyote_timer = 0

    def get_rect(self):
        return pygame.Rect(self.px, self.py, self.width, self.height)

    def update(self, game):
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1
        if self.coyote_timer > 0:
            self.coyote_timer -= 1

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

        if self.on_ground:
            self.coyote_timer = self.coyote_frames

        if self.jump_buffer_timer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.jump()
            self.jump_buffer_timer = 0
            self.coyote_timer = 0
            game.steps += 1

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

        # Cycle Alma's walking frames while A/D movement is active.
        if self.move_direction in ["left", "right"]:
            self.anim_timer += 1
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 3
        else:
            self.anim_timer = 0
            self.anim_frame = 0

    def jump(self):
        self.vy = self.jump_force
        self.on_ground = False

    def request_jump(self):
        self.jump_buffer_timer = self.jump_buffer_frames

    def draw(self, game, ox, oy):
        rect = self.get_rect().move(ox, oy)
        image = None
        if self.move_direction in ["left", "right"]:
            frames = game.assets.get(f"{self.move_direction}_frames", [])
            if len(frames) == 3 and all(frames):
                image = frames[self.anim_frame]
        if image is None:
            image = game.assets.get("stand") or game.assets.get("alma")

        if image:
            game.screen.blit(image, (rect.x - (TILE_SIZE - self.width)//2, rect.y - (TILE_SIZE - self.height)))
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
        self.view_distance = TILE_SIZE * 3
        
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

    def can_see_player(self, game):
        if game.player_hidden or not game.player:
            return False

        drone_rect = self.get_rect()
        player_rect = game.player.get_rect()
        vision_top = drone_rect.centery - TILE_SIZE // 2
        vision_rect = pygame.Rect(
            drone_rect.centerx if self.dir > 0 else drone_rect.centerx - self.view_distance,
            vision_top,
            self.view_distance,
            TILE_SIZE
        )

        if not vision_rect.colliderect(player_rect):
            return False

        drone_center = drone_rect.center
        player_center = player_rect.center
        for tile in game.get_solid_rects():
            if tile.clipline(drone_center, player_center):
                return False
        return True

    def draw(self, game, ox, oy):
        rect = self.get_rect().move(ox, oy)
        cone_length = self.view_distance
        cone_color = (255, 80, 40, 58)
        if game.player_hidden:
            cone_color = (0, 255, 200, 28)

        if self.dir > 0:
            points = [
                (rect.centerx, rect.centery),
                (rect.centerx + cone_length, rect.centery - TILE_SIZE // 2),
                (rect.centerx + cone_length, rect.centery + TILE_SIZE // 2)
            ]
        else:
            points = [
                (rect.centerx, rect.centery),
                (rect.centerx - cone_length, rect.centery - TILE_SIZE // 2),
                (rect.centerx - cone_length, rect.centery + TILE_SIZE // 2)
            ]
        cone_surface = pygame.Surface((game.win_w, game.win_h), pygame.SRCALPHA)
        pygame.draw.polygon(cone_surface, cone_color, points)
        game.screen.blit(cone_surface, (0, 0))

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
            game.screen.blit(game.assets["generator"], draw_rect.topleft)
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

class CircuitNode:
    def __init__(self, x, y, label="C"):
        self.grid_x = x
        self.grid_y = y
        self.label = label
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.activated = False

    def draw(self, game, ox, oy):
        draw_rect = self.rect.move(ox, oy)
        base_color = (24, 35, 54)
        line_color = COLOR_GREEN if self.activated else COLOR_YELLOW
        pygame.draw.rect(game.screen, base_color, draw_rect.inflate(-10, -10), border_radius=8)
        pygame.draw.rect(game.screen, line_color, draw_rect.inflate(-10, -10), 3, border_radius=8)
        pygame.draw.line(game.screen, line_color, (draw_rect.left + 18, draw_rect.centery), (draw_rect.right - 18, draw_rect.centery), 3)
        pygame.draw.circle(game.screen, line_color, draw_rect.center, 8, 2)
        lbl = get_font(20, bold=True).render(self.label, True, COLOR_BG if self.activated else COLOR_WHITE)
        self_center = (draw_rect.centerx - lbl.get_width() // 2, draw_rect.centery - lbl.get_height() // 2)
        game.screen.blit(lbl, self_center)
        if self.activated:
            pulse = int(140 + 90 * math.sin(pygame.time.get_ticks() * 0.012))
            glow = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            pygame.draw.circle(glow, COLOR_GREEN + (pulse,), (TILE_SIZE // 2, TILE_SIZE // 2), 20)
            game.screen.blit(glow, draw_rect.topleft)

class RadioBeacon:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def draw(self, game, ox, oy):
        draw_rect = self.rect.move(ox, oy)
        pygame.draw.rect(game.screen, (18, 40, 80), draw_rect)
        pygame.draw.rect(game.screen, COLOR_CYAN, draw_rect, 3, border_radius=8)
        center = draw_rect.center
        pygame.draw.circle(game.screen, COLOR_CYAN, center, 10, 2)
        pygame.draw.circle(game.screen, COLOR_WHITE, center, 3)

class ShadowZone:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def draw(self, game, ox, oy):
        draw_rect = self.rect.move(ox, oy)
        shadow = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        shadow.fill(COLOR_SHADOW + (150,))
        pygame.draw.rect(shadow, COLOR_CYAN + (65,), shadow.get_rect(), 2, border_radius=4)
        game.screen.blit(shadow, draw_rect.topleft)

# ==============================================================================
# MAIN GAME CLASS (ENGINE, STATE MANAGEMENT, EVENT LOOP)
# ==============================================================================
class Game:
    def __init__(self):
        self.level_files = [
            "levels/level1.txt",
            "levels/level2.txt",
            "levels/level3.txt"
        ]
        self.level_configs = {
            "levels/level1.txt": {
                "target_frequency": 104.5,
                "hint": "La baliza usa base 100.5 y suma energia por nodo restaurado.",
                "puzzle_mode": "restore_all",
                "puzzle_name": "Red de energia",
                "puzzle_hint": "Activa todos los nodos C antes del generador.",
                "required_bandwidth": "WIDE",
                "required_signal_code": "A",
                "frequency_window": 0.12,
                "stability_required": 35,
                "tuning_hint": "Logica: base 100.5 + 2.0 MHz por cada nodo C restaurado. Emergencia = banda ancha, canal inicial."
            },
            "levels/level2.txt": {
                "target_frequency": 95.3,
                "hint": "La secuencia de reles tambien codifica la portadora.",
                "puzzle_mode": "sequence",
                "puzzle_name": "Secuencia de reles",
                "puzzle_hint": "Orden de arranque: 2 -> 1 -> 3.",
                "sequence": ["2", "1", "3"],
                "required_bandwidth": "NARROW",
                "required_signal_code": "B",
                "frequency_window": 0.09,
                "stability_required": 70,
                "tuning_hint": "Logica: los reles 2-1-3 entregan digitos 9-5-3. Usa decimal antes del ultimo digito. El filtro de ruido pide banda estrecha."
            },
            "levels/level3.txt": {
                "target_frequency": 100.7,
                "hint": "El transmisor final suma el pulso decimal a la portadora base.",
                "puzzle_mode": "polarity",
                "puzzle_name": "Matriz de polaridad",
                "puzzle_hint": "Cada panel alterna otros circuitos: busca dejar todo en verde.",
                "initial_active": {"1": False, "2": True, "3": False},
                "polarity_links": {
                    "1": ["1", "2"],
                    "2": ["1", "2", "3"],
                    "3": ["2", "3"]
                },
                "required_bandwidth": "PULSE",
                "required_signal_code": "C",
                "frequency_window": 0.06,
                "stability_required": 105,
                "signal_noise": 0.18,
                "tuning_hint": "Logica: matriz completa = 100 MHz + pulso final 0.7. Solo responde a pulsos cifrados del tercer canal."
            }
        }
        self.level_index = 0
        self.level_data = []
        self.grid_w = 0
        self.grid_h = 0
        self.current_frequency = 88.5
        self.target_frequency = 104.5
        self.freq_connected = False
        self.level_hint = ""
        self.puzzle_mode = "restore_all"
        self.puzzle_name = ""
        self.puzzle_hint = ""
        self.sequence_target = []
        self.sequence_index = 0
        self.initial_active = {}
        self.polarity_links = {}
        self.puzzle_feedback = ""
        self.puzzle_feedback_timer = 0
        self.bandwidth_options = ["WIDE", "NARROW", "PULSE"]
        self.signal_code_options = ["A", "B", "C"]
        self.current_bandwidth = "WIDE"
        self.current_signal_code = "A"
        self.required_bandwidth = "WIDE"
        self.required_signal_code = "A"
        self.frequency_window = 0.1
        self.stability_required = 45
        self.stability_frames = 0
        self.signal_noise = 0.0
        self.tuning_hint = ""
        self.radio_beacons = []
        self.load_current_level()
        
        # Setup Pygame screen size and window caption
        self.screen = None
        self.configure_screen()
        pygame.display.set_caption("Ecos de la Cordillera: Estaciones")
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
        self.near_circuit_msg = False
        self.near_circuit = None
        self.player_hidden = False
        self.last_failure = ""
        
        self.reset_game()

    def configure_screen(self):
        self.win_w = self.grid_w * TILE_SIZE
        self.win_h = self.grid_h * TILE_SIZE + HUD_HEIGHT
        self.screen = pygame.display.set_mode((self.win_w, self.win_h))

    def load_current_level(self):
        filename = self.level_files[self.level_index]
        self.load_level(filename)
        config = self.level_configs.get(filename, {})
        self.target_frequency = config.get("target_frequency", 104.5)
        self.level_hint = config.get("hint", "Busca la frecuencia correcta para activar la puerta.")
        self.current_frequency = max(88.0, min(108.0, self.target_frequency - 4.0))
        self.puzzle_mode = config.get("puzzle_mode", "restore_all")
        self.puzzle_name = config.get("puzzle_name", "Circuitos")
        self.puzzle_hint = config.get("puzzle_hint", "Restaura los circuitos antes de activar el generador.")
        self.sequence_target = config.get("sequence", [])
        self.initial_active = config.get("initial_active", {})
        self.polarity_links = config.get("polarity_links", {})
        self.required_bandwidth = config.get("required_bandwidth", "WIDE")
        self.required_signal_code = config.get("required_signal_code", "A")
        self.frequency_window = config.get("frequency_window", 0.1)
        self.stability_required = config.get("stability_required", 45)
        self.signal_noise = config.get("signal_noise", 0.0)
        self.tuning_hint = config.get("tuning_hint", "Ajusta la frecuencia y bloquea el enlace.")

    def restart_from_first_level(self):
        self.level_index = 0
        self.load_current_level()
        self.configure_screen()
        self.reset_game()

    def advance_level(self):
        if self.level_index < len(self.level_files) - 1:
            self.level_index += 1
            self.load_current_level()
            self.configure_screen()
            self.state = "PLAYING"
            self.reset_game()
        else:
            self.state = "WON"

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
        if any(len(row) != self.grid_w for row in self.level_data):
            raise ValueError(f"Every row in {filename} must have the same width.")

    def load_assets(self):
        self.assets = {}
        paths = {
            "floor": "assets/floor.png",
            "wall": "assets/wall.png",
            "door": "assets/door.png",
            "alma": "assets/alma.png",
            "stand": "assets/stand.png",
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

        for direction in ["right", "left"]:
            self.assets[f"{direction}_frames"] = []
            for index in range(3):
                path = f"assets/{direction}{index}.png"
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                        self.assets[f"{direction}_frames"].append(img)
                    except Exception as e:
                        print(f"Error loading {path}: {e}")
                        self.assets[f"{direction}_frames"].append(None)
                else:
                    self.assets[f"{direction}_frames"].append(None)

    def reset_game(self):
        self.start_time = pygame.time.get_ticks()
        self.particles.clear()
        self.shake_intensity = 0
        self.steps = 0
        self.current_frequency = max(88.0, min(108.0, self.target_frequency - 4.0))
        self.freq_connected = False
        self.near_generator_msg = False
        self.near_radio_hint = False
        self.near_circuit_msg = False
        self.near_circuit = None
        self.player_hidden = False
        self.last_failure = ""
        self.sequence_index = 0
        self.puzzle_feedback = ""
        self.puzzle_feedback_timer = 0
        self.current_bandwidth = "WIDE"
        self.current_signal_code = "A"
        self.stability_frames = 0
        
        self.drones = []
        self.solids = []
        self.player = None
        self.generator = None
        self.door_rect = None
        self.radio_beacons = []
        self.circuit_nodes = []
        self.shadow_zones = []

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
                elif ch == 'R':
                    self.radio_beacons.append(RadioBeacon(c, r))
                elif ch in ['C', '1', '2', '3']:
                    node = CircuitNode(c, r, ch)
                    node.activated = self.initial_active.get(ch, False)
                    self.circuit_nodes.append(node)
                elif ch == 'S':
                    self.shadow_zones.append(ShadowZone(c, r))

    def get_solid_rects(self):
        return self.solids

    def circuits_powered(self):
        if self.puzzle_mode == "sequence":
            return self.sequence_index >= len(self.sequence_target) and len(self.sequence_target) > 0
        return all(node.activated for node in self.circuit_nodes)

    def circuit_interactable(self, node):
        if self.puzzle_mode == "polarity":
            return True
        return not node.activated

    def puzzle_progress_text(self):
        if self.puzzle_mode == "sequence":
            return f"{self.sequence_index}/{len(self.sequence_target)}"
        active_nodes = sum(1 for node in self.circuit_nodes if node.activated)
        return f"{active_nodes}/{len(self.circuit_nodes)}"

    def set_puzzle_feedback(self, message):
        self.puzzle_feedback = message
        self.puzzle_feedback_timer = FPS * 2

    def frequency_aligned(self):
        return abs(self.current_frequency - self.target_frequency) <= self.frequency_window

    def bandwidth_aligned(self):
        return self.current_bandwidth == self.required_bandwidth

    def signal_code_aligned(self):
        return self.current_signal_code == self.required_signal_code

    def tuning_requirements_met(self):
        return self.frequency_aligned() and self.bandwidth_aligned() and self.signal_code_aligned()

    def frequency_diagnostic(self):
        if self.frequency_aligned():
            return "CARRIER LOCK RANGE"
        if self.current_frequency < self.target_frequency:
            return "CARRIER LOW"
        return "CARRIER HIGH"

    def filter_diagnostic(self):
        return "FILTER ACCEPTED" if self.bandwidth_aligned() else "FILTER REJECTED"

    def handshake_diagnostic(self):
        return "HANDSHAKE OK" if self.signal_code_aligned() else "NO HANDSHAKE"

    def tuning_progress(self):
        if self.stability_required <= 0:
            return 1.0
        return max(0.0, min(1.0, self.stability_frames / self.stability_required))

    def signal_strength(self):
        diff = abs(self.current_frequency - self.target_frequency)
        freq_score = max(0.0, 1.0 - diff / max(self.frequency_window * 5, 0.1))
        band_score = 1.0 if self.bandwidth_aligned() else 0.55
        code_score = 1.0 if self.signal_code_aligned() else 0.65
        noise = self.signal_noise * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.012))
        return max(0.0, min(1.0, freq_score * band_score * code_score - noise))

    def adjust_frequency(self, delta):
        self.current_frequency = round(max(88.0, min(108.0, self.current_frequency + delta)), 1)
        if not self.frequency_aligned():
            self.stability_frames = max(0, self.stability_frames - 10)

    def cycle_bandwidth(self):
        current_index = self.bandwidth_options.index(self.current_bandwidth)
        self.current_bandwidth = self.bandwidth_options[(current_index + 1) % len(self.bandwidth_options)]
        self.stability_frames = 0

    def cycle_signal_code(self):
        current_index = self.signal_code_options.index(self.current_signal_code)
        self.current_signal_code = self.signal_code_options[(current_index + 1) % len(self.signal_code_options)]
        self.stability_frames = 0

    def interact_circuit(self, node):
        if self.puzzle_mode == "sequence":
            expected = self.sequence_target[self.sequence_index] if self.sequence_index < len(self.sequence_target) else None
            if node.label == expected:
                node.activated = True
                self.sequence_index += 1
                self.set_puzzle_feedback(f"Rele {node.label} sincronizado.")
            else:
                for circuit in self.circuit_nodes:
                    circuit.activated = False
                self.sequence_index = 0
                self.set_puzzle_feedback("Secuencia incorrecta: reles reiniciados.")
                self.add_explosion(node.rect.centerx, node.rect.centery, COLOR_ORANGE)
                self.trigger_shake(5)
                return
        elif self.puzzle_mode == "polarity":
            labels_to_toggle = self.polarity_links.get(node.label, [node.label])
            for circuit in self.circuit_nodes:
                if circuit.label in labels_to_toggle:
                    circuit.activated = not circuit.activated
            self.set_puzzle_feedback(f"Polaridad {node.label} alternada.")
        else:
            node.activated = True
            self.set_puzzle_feedback(f"Nodo {node.label} restaurado.")

        self.add_explosion(node.rect.centerx, node.rect.centery, COLOR_GREEN)
        self.trigger_shake(4)

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
            if self.puzzle_feedback_timer > 0:
                self.puzzle_feedback_timer -= 1
            else:
                self.puzzle_feedback = ""
            
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

            self.near_circuit_msg = False
            self.near_circuit = None
            for node in self.circuit_nodes:
                if self.circuit_interactable(node) and self.player.get_rect().colliderect(node.rect.inflate(22, 22)):
                    self.near_circuit_msg = True
                    self.near_circuit = node
                    break

            self.player_hidden = any(
                self.player.get_rect().colliderect(zone.rect.inflate(8, 8))
                for zone in self.shadow_zones
            )

            # Check if player is near a radio beacon for narrative hint
            self.near_radio_hint = False
            for beacon in self.radio_beacons:
                if self.player.get_rect().colliderect(beacon.rect.inflate(20, 20)):
                    self.near_radio_hint = True
                    break

            # Drone collisions
            p_rect = self.player.get_rect()
            for d in self.drones:
                if p_rect.colliderect(d.get_rect()):
                    self.last_failure = "Alma fue alcanzada por un drone de patrulla."
                    self.state = "GAME_OVER"
                    self.add_explosion(p_rect.centerx, p_rect.centery, COLOR_RED)
                    self.trigger_shake(16)
                    break
                if d.can_see_player(self):
                    self.last_failure = "Alma fue detectada fuera de las zonas de sombra."
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
                self.last_failure = "Alma cayo fuera de la estacion."
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
            if self.tuning_requirements_met():
                self.stability_frames = min(self.stability_required, self.stability_frames + 1)
            else:
                self.stability_frames = max(0, self.stability_frames - 2)

            self.freq_connected = self.stability_frames >= self.stability_required
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

            # Draw shadow cover zones
            for zone in self.shadow_zones:
                zone.draw(self, ox, oy)

            # Draw Generator
            if self.generator:
                self.generator.draw(self, ox, oy)

            # Draw circuit nodes
            for node in self.circuit_nodes:
                node.draw(self, ox, oy)

            # Draw Radio Beacons
            for beacon in self.radio_beacons:
                beacon.draw(self, ox, oy)

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
        font_info = get_font(20)
        lbl_jumps = font_info.render(f"JUMPS: {self.steps}", True, COLOR_WHITE)
        lbl_time = font_info.render(f"TIME: {self.elapsed_time}s", True, COLOR_WHITE)
        lbl_level = font_info.render(f"LEVEL: {self.level_index + 1}/{len(self.level_files)}", True, COLOR_WHITE)
        lbl_circuits = font_info.render(f"{self.puzzle_name.upper()}: {self.puzzle_progress_text()}", True, COLOR_GREEN if self.circuits_powered() else COLOR_YELLOW)
        
        status_text = "DOOR LOCKED: RESTORE CIRCUITS"
        status_color = COLOR_RED
        if self.circuits_powered():
            status_text = "CIRCUITS READY: ACTIVATE GENERATOR"
            status_color = COLOR_YELLOW
        if self.generator and self.generator.activated:
            status_text = "GENERATOR ACTIVE: PROCEED TO PORTAL"
            status_color = COLOR_CYAN
            
        lbl_status = font.render(status_text, True, status_color)
        
        self.screen.blit(lbl_status, (20, hud_rect.top + 15))
        info_x = self.win_w - 20
        for label in [lbl_time, lbl_jumps, lbl_level, lbl_circuits]:
            info_x -= label.get_width()
            self.screen.blit(label, (info_x, hud_rect.top + 18))
            info_x -= 24
        
        # Interactions tips
        font_sub = get_font(18)
        if self.puzzle_feedback:
            feedback_color = COLOR_ORANGE if "incorrecta" in self.puzzle_feedback else COLOR_GREEN
            lbl_tip = font_sub.render(f">> {self.puzzle_feedback.upper()} <<", True, feedback_color)
        elif self.near_circuit_msg:
            lbl_tip = font_sub.render(f">> PANEL {self.near_circuit.label}: PRESS [E] | {self.puzzle_name.upper()} {self.puzzle_progress_text()} <<", True, COLOR_YELLOW)
        elif self.near_generator_msg and not self.circuits_powered():
            lbl_tip = font_sub.render(f">> {self.puzzle_hint.upper()} <<", True, COLOR_ORANGE)
        elif self.near_generator_msg:
            lbl_tip = font_sub.render(">> PRESS [E] TO ACTIVATE POWER GENERATOR <<", True, COLOR_YELLOW)
        elif self.near_radio_hint:
            lbl_tip = font_sub.render(f">> RADIO HINT: {self.level_hint} <<", True, COLOR_CYAN)
        elif self.player_hidden:
            lbl_tip = font_sub.render(">> SHADOW COVER ACTIVE: DRONE VISION IS DISRUPTED <<", True, COLOR_CYAN)
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
            "Operator: ALMA RIOS",
            "Environment: Cordillera Radio Stations",
            "Mission Instructions:",
            "  1. Solve each station's circuit puzzle [E].",
            "  2. Use shadow cover to avoid drone vision.",
            "  3. Activate the generator, reach the gate and tune the MHz signal."
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

    def draw_centered_wrapped_text(self, text, font, color, center_x, start_y, max_width, line_gap=4):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test_line = word if not current else f"{current} {word}"
            if font.size(test_line)[0] <= max_width:
                current = test_line
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        y = start_y
        for line in lines:
            rendered = font.render(line, True, color)
            self.screen.blit(rendered, (center_x - rendered.get_width() // 2, y))
            y += rendered.get_height() + line_gap
        return y

    def draw_tuning_screen(self):
        # Semi-transparent dark blue overlay
        overlay = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        overlay.fill((5, 10, 25, 230))
        self.screen.blit(overlay, (0, 0))
        
        # Center box
        box_w, box_h = 660, 500
        box_rect = pygame.Rect(self.win_w//2 - box_w//2, self.win_h//2 - box_h//2 - 20, box_w, box_h)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, box_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_CYAN, box_rect, 2, border_radius=10)
        
        font_title = get_font(32, bold=True)
        lbl_head = font_title.render("ANTENNA LINK TUNER", True, COLOR_CYAN)
        self.screen.blit(lbl_head, (box_rect.centerx - lbl_head.get_width()//2, box_rect.top + 25))
        
        # Draw Frequency display
        font_freq = get_font(52, bold=True)
        freq_str = f"{self.current_frequency:.1f} MHz"
        freq_color = COLOR_GREEN if self.frequency_aligned() else COLOR_ORANGE
        lbl_freq = font_freq.render(freq_str, True, freq_color)
        self.screen.blit(lbl_freq, (box_rect.centerx - lbl_freq.get_width()//2, box_rect.top + 90))
        
        # Clue and diagnostics
        font_detail = get_font(20)
        lbl_target = font_detail.render("SIGNAL ANALYSIS: infer the carrier from the station clue", True, COLOR_WHITE)
        self.screen.blit(lbl_target, (box_rect.centerx - lbl_target.get_width()//2, box_rect.top + 160))
        self.draw_centered_wrapped_text(
            self.tuning_hint,
            get_font(17),
            COLOR_CYAN,
            box_rect.centerx,
            box_rect.top + 190,
            box_w - 90
        )
        
        # Tuner slider visual
        slider_y = box_rect.top + 245
        pygame.draw.line(self.screen, COLOR_GRAY, (box_rect.left + 50, slider_y), (box_rect.right - 50, slider_y), 4)
        
        # Map current frequency ratio to slider position
        min_f, max_f = 88.0, 108.0
        ratio = (self.current_frequency - min_f) / (max_f - min_f)
        ratio = max(0.0, min(1.0, ratio))
        slider_x = int(box_rect.left + 50 + ratio * (box_w - 100))
        
        # Slider handle
        pygame.draw.rect(self.screen, COLOR_WHITE, (slider_x - 6, slider_y - 15, 12, 30), border_radius=3)

        # Bandwidth and code selectors
        font_label = get_font(18, bold=True)
        selector_y = box_rect.top + 290
        band_color = COLOR_GREEN if self.bandwidth_aligned() else COLOR_ORANGE
        code_color = COLOR_GREEN if self.signal_code_aligned() else COLOR_ORANGE
        band_text = font_label.render(f"BAND: {self.current_bandwidth}", True, band_color)
        code_text = font_label.render(f"CODE: {self.current_signal_code}", True, code_color)
        pygame.draw.rect(self.screen, (18, 28, 46), (box_rect.left + 55, selector_y - 10, 250, 38), border_radius=6)
        pygame.draw.rect(self.screen, band_color, (box_rect.left + 55, selector_y - 10, 250, 38), 2, border_radius=6)
        pygame.draw.rect(self.screen, (18, 28, 46), (box_rect.right - 305, selector_y - 10, 250, 38), border_radius=6)
        pygame.draw.rect(self.screen, code_color, (box_rect.right - 305, selector_y - 10, 250, 38), 2, border_radius=6)
        self.screen.blit(band_text, (box_rect.left + 70, selector_y))
        self.screen.blit(code_text, (box_rect.right - 290, selector_y))

        diag_y = box_rect.top + 325
        diag_font = get_font(16, bold=True)
        diagnostics = [
            (self.frequency_diagnostic(), COLOR_GREEN if self.frequency_aligned() else COLOR_ORANGE),
            (self.filter_diagnostic(), COLOR_GREEN if self.bandwidth_aligned() else COLOR_ORANGE),
            (self.handshake_diagnostic(), COLOR_GREEN if self.signal_code_aligned() else COLOR_ORANGE)
        ]
        diag_x = box_rect.left + 60
        for text, color in diagnostics:
            label = diag_font.render(text, True, color)
            pygame.draw.rect(self.screen, (18, 28, 46), (diag_x - 10, diag_y - 6, label.get_width() + 20, 28), border_radius=5)
            pygame.draw.rect(self.screen, color, (diag_x - 10, diag_y - 6, label.get_width() + 20, 28), 1, border_radius=5)
            self.screen.blit(label, (diag_x, diag_y))
            diag_x += label.get_width() + 34

        # Signal and stability bars
        bar_x = box_rect.left + 60
        bar_w = box_w - 120
        strength_y = box_rect.top + 365
        stability_y = box_rect.top + 395
        strength = self.signal_strength()
        stability = self.tuning_progress()
        for y, label, value, color in [
            (strength_y, "SIGNAL", strength, COLOR_CYAN),
            (stability_y, "STABILITY", stability, COLOR_GREEN if self.freq_connected else COLOR_YELLOW)
        ]:
            pygame.draw.rect(self.screen, (25, 32, 48), (bar_x, y, bar_w, 12), border_radius=4)
            pygame.draw.rect(self.screen, color, (bar_x, y, int(bar_w * value), 12), border_radius=4)
            txt = get_font(16).render(label, True, COLOR_WHITE)
            self.screen.blit(txt, (bar_x, y - 18))
        
        # Oscilloscope visual effect in the center box
        wave_surface = pygame.Surface((box_w - 80, 42), pygame.SRCALPHA)
        wave_pts = []
        freq_diff = abs(self.current_frequency - self.target_frequency)
        wave_speed = pygame.time.get_ticks() * 0.02
        amplitude = 4.0 + self.signal_strength() * 18.0
        frequency_mod = 0.05 + (0.2 / max(0.1, freq_diff))
        
        for wx in range(box_w - 80):
            noise = self.signal_noise * 18.0 * math.sin(wx * 0.43 + wave_speed * 2)
            wy = 21 + amplitude * math.sin(wx * frequency_mod + wave_speed) + noise
            wave_pts.append((wx, int(wy)))
            
        if len(wave_pts) > 1:
            color = COLOR_GREEN if self.freq_connected else COLOR_CYAN
            pygame.draw.lines(wave_surface, color, False, wave_pts, 2)
        self.screen.blit(wave_surface, (box_rect.left + 40, box_rect.top + 407))
        
        # Action prompts
        font_prompt = get_font(20)
        if self.freq_connected:
            pulse = int(127 + 128 * math.sin(pygame.time.get_ticks() * 0.007))
            lbl_act = font_prompt.render("LINK LOCKED! PRESS SPACE TO OPEN THE GATE", True, (pulse, 255, pulse))
        else:
            lbl_act = font_prompt.render("Q/E tune MHz  |  TAB band  |  1/2/3 code  |  hold lock to stabilize", True, COLOR_WHITE)
            
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
        detail = self.last_failure or "Alma fell or was detected by a mountain patrol drone."
        lbl_detail = font_stats.render(detail, True, COLOR_WHITE)
        
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
                            self.restart_from_first_level()
                            
                    elif self.state == "PLAYING":
                        # Jump Triggers
                        if event.key in [pygame.K_w, pygame.K_UP, pygame.K_SPACE]:
                            self.player.request_jump()
                        # Interact Generator
                        elif event.key == pygame.K_e:
                            if self.near_circuit_msg and self.near_circuit:
                                self.interact_circuit(self.near_circuit)
                            elif self.near_generator_msg and self.generator:
                                if not self.circuits_powered():
                                    g_center = self.generator.rect.center
                                    self.add_explosion(g_center[0], g_center[1], COLOR_ORANGE)
                                    self.trigger_shake(4)
                                    continue
                                self.generator.activated = True
                                self.near_generator_msg = False
                                # Sprout particles from generator
                                g_center = self.generator.rect.center
                                self.add_explosion(g_center[0], g_center[1], COLOR_GREEN)
                                self.trigger_shake(6)
                                
                    elif self.state == "TUNING":
                        # Tune radio with Q/E
                        if event.key == pygame.K_q:
                            self.adjust_frequency(-0.1)
                        elif event.key == pygame.K_e:
                            self.adjust_frequency(0.1)
                        elif event.key == pygame.K_TAB:
                            self.cycle_bandwidth()
                        elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                            code_index = [pygame.K_1, pygame.K_2, pygame.K_3].index(event.key)
                            self.current_signal_code = self.signal_code_options[code_index]
                            self.stability_frames = 0
                        elif event.key == pygame.K_SPACE:
                            if self.freq_connected:
                                door_center = self.door_rect.center
                                self.add_explosion(door_center[0], door_center[1], COLOR_GREEN)
                                self.trigger_shake(12)
                                self.advance_level()
                                
                    elif self.state == "WON":
                        if event.key == pygame.K_SPACE:
                            self.state = "PLAYING"
                            self.restart_from_first_level()
                            
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
                    self.player.move_direction = "left"
                    self.player.facing = "left"
                elif right_pressed and not left_pressed:
                    self.player.vx = self.player.walk_speed
                    self.player.move_direction = "right"
                    self.player.facing = "right"
                else:
                    self.player.vx = 0.0
                    self.player.move_direction = "idle"

            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
