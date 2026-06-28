import pygame


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
