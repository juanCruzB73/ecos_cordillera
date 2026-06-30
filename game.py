import pygame
import sys
import os
import math
import random

from constants import (
    TILE_SIZE, HUD_HEIGHT, FPS,
    COLOR_BG, COLOR_HUD_BG, COLOR_CYAN, COLOR_ORANGE,
    COLOR_GREEN, COLOR_RED, COLOR_WHITE, COLOR_GRAY, COLOR_YELLOW,
    get_font,
)
from particle import Particle
from player import Player
from drone import Drone
from objects import Generator, CircuitNode, RadioBeacon, ShadowZone


class Game:
    def __init__(self):
        self.level_files = [
            "levels/level0.txt",
            "levels/level1.txt",
            "levels/level2.txt",
            "levels/level3.txt"
        ]
        self.level_configs = {
            "levels/level0.txt": {
                "target_frequency": 90.0,
                "hint": "Tutorial: Sigue las instrucciones para aprender los controles.",
                "puzzle_mode": "restore_all",
                "puzzle_name": "Tutorial",
                "puzzle_hint": "Activa el generador primero.",
                "required_bandwidth": "WIDE",
                "required_signal_code": "A",
                "frequency_window": 0.12,
                "stability_required": 20,
                "tuning_hint": "Tutorial: Sintoniza la frecuencia a 90.0 MHz usando Q/E."
            },
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

        self.screen = None
        self.configure_screen()
        pygame.display.set_caption("Ecos de la Cordillera: Estaciones")
        self.clock = pygame.time.Clock()

        self.load_assets()

        self.current_frequency = 88.5
        self.target_frequency = 104.5
        self.freq_connected = False

        self.state = "START"
        self.particles = []
        self.shake_intensity = 0
        self.shake_decay = 0.9
        self.shake_x = 0
        self.shake_y = 0

        self.steps = 0
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
        self.countdown = 100
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
        if self.shake_intensity > 0.5:
            self.shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= self.shake_decay
        else:
            self.shake_x = 0
            self.shake_y = 0

        if self.state == "PLAYING":
            self.elapsed_time = (pygame.time.get_ticks() - self.start_time) // 1000
            self.countdown = max(0, 100 - self.elapsed_time)
            if self.countdown == 0:
                self.last_failure = "Alma se quedó sin tiempo."
                self.state = "GAME_OVER"
                p_rect = self.player.get_rect()
                self.add_explosion(p_rect.centerx, p_rect.centery, COLOR_RED)
                self.trigger_shake(16)
                return
            if self.puzzle_feedback_timer > 0:
                self.puzzle_feedback_timer -= 1
            else:
                self.puzzle_feedback = ""

            self.player.update(self)

            for d in self.drones:
                d.update(self)

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

            self.near_radio_hint = False
            for beacon in self.radio_beacons:
                if self.player.get_rect().colliderect(beacon.rect.inflate(20, 20)):
                    self.near_radio_hint = True
                    break

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

            if self.door_rect and p_rect.colliderect(self.door_rect):
                if self.generator and self.generator.activated:
                    self.state = "TUNING"
                else:
                    if random.random() < 0.1:
                        self.add_explosion(self.door_rect.centerx, self.door_rect.centery, COLOR_ORANGE)

            if self.player.py > self.grid_h * TILE_SIZE:
                self.last_failure = "Alma cayo fuera de la estacion."
                self.state = "GAME_OVER"
                self.trigger_shake(10)

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

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw_background(self):
        for r in range(self.grid_h):
            for c in range(self.grid_w):
                x = c * TILE_SIZE + self.shake_x
                y = r * TILE_SIZE + self.shake_y
                if self.assets.get("floor"):
                    self.screen.blit(self.assets["floor"], (x, y))
                else:
                    rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(self.screen, (15, 20, 35), rect)
                    pygame.draw.rect(self.screen, (18, 24, 42), rect, 1)

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

            for block in self.solids:
                draw_rect = block.move(ox, oy)
                if self.assets.get("wall"):
                    self.screen.blit(self.assets["wall"], draw_rect.topleft)
                else:
                    pygame.draw.rect(self.screen, (32, 40, 58), draw_rect)
                    pygame.draw.rect(self.screen, (45, 55, 78), draw_rect, 2)

            for zone in self.shadow_zones:
                zone.draw(self, ox, oy)

            if self.generator:
                self.generator.draw(self, ox, oy)

            for node in self.circuit_nodes:
                node.draw(self, ox, oy)

            for beacon in self.radio_beacons:
                beacon.draw(self, ox, oy)

            if self.door_rect:
                draw_rect = self.door_rect.move(ox, oy)
                if self.assets.get("door"):
                    self.screen.blit(self.assets["door"], draw_rect.topleft)
                else:
                    door_color = COLOR_CYAN if (self.generator and self.generator.activated) else COLOR_RED
                    pygame.draw.rect(self.screen, door_color, draw_rect, border_radius=4)
                    pygame.draw.rect(self.screen, COLOR_BG, draw_rect.inflate(-16, -16), border_radius=4)

            for d in self.drones:
                d.draw(self, ox, oy)

            if self.state != "GAME_OVER" and self.player:
                self.player.draw(self, ox, oy)

            for p in self.particles:
                p.draw(self.screen, ox, oy)

            if self.level_index == 0 and self.state == "PLAYING":
                tutorial_font = get_font(22, bold=True)
                tutorial_text = ""
                if self.generator and not self.generator.activated:
                    if self.player.px < 350:
                        tutorial_text = "TUTORIAL: Usa A/D o Flechas para moverte."
                    elif 350 <= self.player.px < 600:
                        tutorial_text = "TUTORIAL: Presiona W, ESPACIO o Flecha Arriba para saltar."
                    else:
                        tutorial_text = "TUTORIAL: Acercate al interruptor y presiona [E] para activarlo."
                else:
                    tutorial_text = "TUTORIAL: ¡Interruptor activo! Ve al portal [E] a la derecha."

                if tutorial_text:
                    txt_surface = tutorial_font.render(tutorial_text, True, COLOR_CYAN)
                    bg_rect = pygame.Rect(self.win_w // 2 - txt_surface.get_width() // 2 - 15, 30, txt_surface.get_width() + 30, 40)
                    box_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(box_surface, (10, 15, 30, 200), (0, 0, bg_rect.width, bg_rect.height), border_radius=6)
                    pygame.draw.rect(box_surface, COLOR_CYAN, (0, 0, bg_rect.width, bg_rect.height), 2, border_radius=6)
                    self.screen.blit(box_surface, bg_rect.topleft)
                    self.screen.blit(txt_surface, (self.win_w // 2 - txt_surface.get_width() // 2, 38))

            self.draw_hud()

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
        countdown_val = getattr(self, "countdown", 100)
        time_color = COLOR_RED if countdown_val <= 20 else (COLOR_YELLOW if countdown_val <= 40 else COLOR_WHITE)
        lbl_time = font_info.render(f"TIME: {countdown_val}s", True, time_color)
        lbl_level = font_info.render(f"LEVEL: {self.level_index + 1}/{len(self.level_files)}", True, COLOR_WHITE)
        lbl_circuits = font_info.render(f"{self.puzzle_name.upper()}: {self.puzzle_progress_text()}", True, COLOR_GREEN if self.circuits_powered() else COLOR_YELLOW)

        if self.level_index == 0:
            status_text = "TUTORIAL: ACTIVA EL INTERRUPTOR (G)"
            status_color = COLOR_YELLOW
            if self.generator and self.generator.activated:
                status_text = "TUTORIAL: INTERRUPTOR ACTIVO - INGRESA AL PORTAL"
                status_color = COLOR_CYAN
        else:
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

        self.screen.blit(lbl_title_shadow, (self.win_w // 2 - lbl_title.get_width() // 2 + 2, 142))
        self.screen.blit(lbl_title, (self.win_w // 2 - lbl_title.get_width() // 2, 140))

        y_offset = 240
        for line in desc_lines:
            color = COLOR_YELLOW if "GENERATOR" in line or "104.5" in line else COLOR_WHITE
            if "Mission Instructions" in line:
                color = COLOR_CYAN
            txt = font_desc.render(line, True, color)
            self.screen.blit(txt, (self.win_w // 2 - txt.get_width() // 2, y_offset))
            y_offset += 32

        self.screen.blit(lbl_start, (self.win_w // 2 - lbl_start.get_width() // 2, self.win_h - 180))

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

    def draw_wrapped_text(self, text, font, color, x, start_y, max_width, line_gap=4):
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
            self.screen.blit(rendered, (x, y))
            y += rendered.get_height() + line_gap
        return y

    def draw_tuning_screen(self):
        overlay = pygame.Surface((self.win_w, self.win_h), pygame.SRCALPHA)
        overlay.fill((5, 10, 25, 230))
        self.screen.blit(overlay, (0, 0))

        total_w = 660 + 20 + 270
        start_x = self.win_w // 2 - total_w // 2

        box_w, box_h = 660, 500
        box_rect = pygame.Rect(start_x, self.win_h // 2 - box_h // 2 - 20, box_w, box_h)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, box_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_CYAN, box_rect, 2, border_radius=10)

        guide_w, guide_h = 270, box_h
        guide_rect = pygame.Rect(box_rect.right + 20, box_rect.top, guide_w, guide_h)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, guide_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_CYAN, guide_rect, 2, border_radius=10)

        font_guide_title = get_font(20, bold=True)
        lbl_guide_title = font_guide_title.render("GUÍA DE SINTONIZACIÓN", True, COLOR_CYAN)
        self.screen.blit(lbl_guide_title, (guide_rect.centerx - lbl_guide_title.get_width() // 2, guide_rect.top + 20))

        guide_items = [
            ("Q", "Bajar frecuencia en pasos de 0.1 MHz."),
            ("E", "Subir frecuencia en pasos de 0.1 MHz."),
            ("TAB", "Cambiar banda entre WIDE, NARROW y PULSE."),
            ("1, 2, 3", "Seleccionar código A, B o C."),
            ("Espacio", "Abrir la puerta cuando el enlace está bloqueado y estabilizado.")
        ]

        font_key = get_font(15, bold=True)
        font_desc = get_font(14)

        gy = guide_rect.top + 60
        for key, desc in guide_items:
            key_lbl = font_key.render(key, True, COLOR_BG)
            key_w = max(35, key_lbl.get_width() + 12)
            key_rect = pygame.Rect(guide_rect.left + 15, gy, key_w, 20)
            pygame.draw.rect(self.screen, COLOR_CYAN, key_rect, border_radius=4)
            self.screen.blit(key_lbl, (key_rect.centerx - key_lbl.get_width() // 2, key_rect.centery - key_lbl.get_height() // 2))
            self.draw_wrapped_text(desc, font_desc, COLOR_WHITE, guide_rect.left + 15, gy + 24, guide_w - 30)
            gy += 82

        font_title = get_font(32, bold=True)
        lbl_head = font_title.render("ANTENNA LINK TUNER", True, COLOR_CYAN)
        self.screen.blit(lbl_head, (box_rect.centerx - lbl_head.get_width() // 2, box_rect.top + 25))

        font_freq = get_font(52, bold=True)
        freq_str = f"{self.current_frequency:.1f} MHz"
        freq_color = COLOR_GREEN if self.frequency_aligned() else COLOR_ORANGE
        lbl_freq = font_freq.render(freq_str, True, freq_color)
        self.screen.blit(lbl_freq, (box_rect.centerx - lbl_freq.get_width() // 2, box_rect.top + 90))

        font_detail = get_font(20)
        lbl_target = font_detail.render("SIGNAL ANALYSIS: infer the carrier from the station clue", True, COLOR_WHITE)
        self.screen.blit(lbl_target, (box_rect.centerx - lbl_target.get_width() // 2, box_rect.top + 160))
        self.draw_centered_wrapped_text(
            self.tuning_hint,
            get_font(17),
            COLOR_CYAN,
            box_rect.centerx,
            box_rect.top + 190,
            box_w - 90
        )

        slider_y = box_rect.top + 245
        pygame.draw.line(self.screen, COLOR_GRAY, (box_rect.left + 50, slider_y), (box_rect.right - 50, slider_y), 4)

        min_f, max_f = 88.0, 108.0
        ratio = (self.current_frequency - min_f) / (max_f - min_f)
        ratio = max(0.0, min(1.0, ratio))
        slider_x = int(box_rect.left + 50 + ratio * (box_w - 100))
        pygame.draw.rect(self.screen, COLOR_WHITE, (slider_x - 6, slider_y - 15, 12, 30), border_radius=3)

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

        font_prompt = get_font(20)
        if self.freq_connected:
            pulse = int(127 + 128 * math.sin(pygame.time.get_ticks() * 0.007))
            lbl_act = font_prompt.render("ENLACE BLOQUEADO! PRESIONA ESPACIO PARA ABRIR LA PUERTA", True, (pulse, 255, pulse))
        else:
            lbl_act = font_prompt.render("Sintoniza con Q/E  |  Banda con TAB  |  Código con 1/2/3", True, COLOR_WHITE)

        self.screen.blit(lbl_act, (box_rect.centerx - lbl_act.get_width() // 2, box_rect.bottom - 40))

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

        self.screen.blit(lbl_win, (self.win_w // 2 - lbl_win.get_width() // 2, self.win_h // 2 - 120))
        self.screen.blit(lbl_stats1, (self.win_w // 2 - lbl_stats1.get_width() // 2, self.win_h // 2 - 30))
        self.screen.blit(lbl_stats2, (self.win_w // 2 - lbl_stats2.get_width() // 2, self.win_h // 2 + 10))
        self.screen.blit(lbl_stats3, (self.win_w // 2 - lbl_stats3.get_width() // 2, self.win_h // 2 + 50))
        self.screen.blit(lbl_restart, (self.win_w // 2 - lbl_restart.get_width() // 2, self.win_h // 2 + 120))

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

        self.screen.blit(lbl_fail, (self.win_w // 2 - lbl_fail.get_width() // 2, self.win_h // 2 - 80))
        self.screen.blit(lbl_detail, (self.win_w // 2 - lbl_detail.get_width() // 2, self.win_h // 2 + 10))
        self.screen.blit(lbl_restart, (self.win_w // 2 - lbl_restart.get_width() // 2, self.win_h // 2 + 80))

    def run(self):
        while True:
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
                        if event.key in [pygame.K_w, pygame.K_UP, pygame.K_SPACE]:
                            self.player.request_jump()
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
                                g_center = self.generator.rect.center
                                self.add_explosion(g_center[0], g_center[1], COLOR_GREEN)
                                self.trigger_shake(6)

                    elif self.state == "TUNING":
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
