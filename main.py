import pygame

pygame.init()
pygame.mixer.init()

from game import Game

if __name__ == "__main__":
    game = Game()
    game.run()
