import pygame
import math

from constants import (
    TILE_SIZE,
    COLOR_GREEN, COLOR_RED, COLOR_GRAY, COLOR_YELLOW,
    COLOR_CYAN, COLOR_WHITE, COLOR_BG, COLOR_SHADOW,
    get_font,
)


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
            pygame.draw.rect(game.screen, (40, 50, 70), draw_rect)
            pygame.draw.rect(game.screen, COLOR_GRAY, draw_rect, 2)

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
