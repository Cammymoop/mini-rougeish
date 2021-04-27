import os, sys
import pygame
import random
from offset import OffsetGroup
from sprite import BasicSprite
from world import GameWorld

from pygame.locals import *
from constants import *

#####################################
# Stuff outside of my restart loop
def initialize():
    pygame.init()

    flags = 0 # to set full screen use FULLSCREEN instead of 0
    real_screen = pygame.display.set_mode((800, 600), flags)

    return real_screen

def shutdown():
    pygame.quit()
# Stuff outside of my restart loop
######################################

# here we go
def main(real_screen):
    if len(sys.argv) > 1:
        GameSettings.game_scale = int(sys.argv[1])
    screen = pygame.Surface((200 * GameSettings.game_scale, 150 * GameSettings.game_scale))
    screen = screen.convert()

    pygame.display.set_caption(random.choice(["Urgh", "Banguin", "Sandomius", "Ess", "Vee Sheem Han", "Spakio", "Gevenera", "Soll Bax Me"]))

    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((8, 20, 30))

    screen.blit(background, (0, 0))

    clock = pygame.time.Clock()

    camera = Rect(0, 0, 1, 1)
    world = GameWorld(clock)

    camera_follow = world.get_player()

    render_list = []
    render_list.append(world)

    # game loop
    running = True
    while running:
        clock.tick(60)
        for event in pygame.event.get(QUIT):
            if event.type == QUIT:
                running = False

        status = world.update()
        running = running and status

        camera.topleft = camera_follow.get_pos()

        # draw stuff
        screen.blit(background, (0, 0))
        for render_obj in render_list:
            render_obj.render(camera, screen)

        real_screen.blit(pygame.transform.scale(screen, (800, 600)), (0, 0))
        pygame.display.flip()

    return world.restart

# standard python start stuffff
if __name__ == "__main__":
    real_screen = initialize()

    restart = True
    while restart:
        restart = main(real_screen)

    shutdown()
