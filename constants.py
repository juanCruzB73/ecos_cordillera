import pygame

TILE_SIZE = 64
HUD_HEIGHT = 80
FPS = 60

COLOR_BG = (10, 14, 26)
COLOR_HUD_BG = (6, 8, 16)
COLOR_CYAN = (0, 255, 200)
COLOR_ORANGE = (255, 110, 0)
COLOR_GREEN = (0, 255, 120)
COLOR_RED = (255, 50, 50)
COLOR_WHITE = (230, 235, 245)
COLOR_GRAY = (100, 110, 130)
COLOR_YELLOW = (255, 215, 0)
COLOR_SHADOW = (12, 18, 32)


def get_font(size, bold=False):
    fonts = ["Consolas", "Courier New", "Lucida Console", "monospace"]
    for f in fonts:
        try:
            return pygame.font.SysFont(f, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)
