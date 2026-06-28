import pygame
import random

from constants import TILE_SIZE, COLOR_CYAN, COLOR_WHITE
from particle import Particle


class Player:
    def __init__(self, x, y):
        self.width = 36
        self.height = 52

        self.px = x * TILE_SIZE + (TILE_SIZE - self.width) // 2
        self.py = y * TILE_SIZE + (TILE_SIZE - self.height)

        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False

        self.gravity = 0.6
        self.terminal_velocity = 12.0
        self.walk_speed = 5.0
        self.jump_force = -14.0

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

        if not self.on_ground:
            self.vy += self.gravity
            if self.vy > self.terminal_velocity:
                self.vy = self.terminal_velocity
        else:
            self.vy = max(0.0, self.vy)

        self.px += self.vx
        rect = self.get_rect()
        for tile in game.get_solid_rects():
            if rect.colliderect(tile):
                if self.vx > 0:
                    self.px = tile.left - self.width
                elif self.vx < 0:
                    self.px = tile.right
                self.vx = 0.0
                rect = self.get_rect()

        self.on_ground = False
        self.py += self.vy
        rect = self.get_rect()
        for tile in game.get_solid_rects():
            if rect.colliderect(tile):
                if self.vy > 0:
                    self.py = tile.top - self.height
                    self.on_ground = True
                    self.vy = 0.0
                elif self.vy < 0:
                    self.py = tile.bottom
                    self.vy = 0.0
                rect = self.get_rect()

        if self.on_ground:
            self.coyote_timer = self.coyote_frames

        if self.jump_buffer_timer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.jump()
            self.jump_buffer_timer = 0
            self.coyote_timer = 0
            game.steps += 1

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
            game.screen.blit(image, (rect.x - (TILE_SIZE - self.width) // 2, rect.y - (TILE_SIZE - self.height)))
        else:
            pygame.draw.rect(game.screen, COLOR_CYAN, rect, border_radius=6)
            pygame.draw.circle(game.screen, COLOR_WHITE, (rect.centerx, rect.y + 15), 8)
