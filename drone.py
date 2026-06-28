import pygame
import random
import math

from constants import TILE_SIZE, COLOR_ORANGE, COLOR_RED
from particle import Particle


class Drone:
    def __init__(self, x, y):
        self.width = 40
        self.height = 40
        self.px = x * TILE_SIZE + (TILE_SIZE - self.width) // 2
        self.py = y * TILE_SIZE + (TILE_SIZE - self.height)
        self.vx = 2.0
        self.dir = 1
        self.view_distance = TILE_SIZE * 3

    def get_rect(self):
        return pygame.Rect(self.px, self.py, self.width, self.height)

    def update(self, game):
        self.px += self.vx * self.dir

        rect = self.get_rect()
        hit_wall = False
        for tile in game.get_solid_rects():
            if rect.colliderect(tile):
                hit_wall = True
                break

        look_offset = self.width if self.dir > 0 else -TILE_SIZE // 2
        test_x = self.px + look_offset
        test_y = self.py + self.height + 4
        test_point = pygame.Rect(test_x, test_y, 4, 4)
        has_ground = False
        for tile in game.get_solid_rects():
            if test_point.colliderect(tile):
                has_ground = True
                break

        if hit_wall or not has_ground:
            self.dir *= -1
            self.px += self.vx * self.dir

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
            game.screen.blit(game.assets["drone"], (rect.x - (TILE_SIZE - self.width) // 2, rect.y - (TILE_SIZE - self.height) // 2))
        else:
            pygame.draw.rect(game.screen, COLOR_ORANGE, rect, border_radius=4)
            pygame.draw.circle(game.screen, COLOR_RED, rect.center, 5)

        glow_pulse = int(140 + 115 * math.sin(pygame.time.get_ticks() * 0.015))
        s = pygame.Surface((20, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (COLOR_ORANGE[0], COLOR_ORANGE[1], COLOR_ORANGE[2], glow_pulse), (0, 0, 20, 8))
        game.screen.blit(s, (rect.centerx - 10, rect.bottom - 4))
