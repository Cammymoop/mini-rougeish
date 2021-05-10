import os, sys
import pygame
import pygame.freetype as pygame_freetype
import random
import math

from offset import OffsetGroup
from sprite import BasicSprite
from world import GameWorld
from text import MonoFont, MonoText

from pygame.locals import *
from constants import *

#####################################
# Stuff outside of my restart loop
def initialize():
    pygame.init()

    flags = 0 # to set full screen use FULLSCREEN instead of 0
    screen_info = pygame.display.Info()

    print('screen info', screen_info.current_w, screen_info.current_h)
    print('calc scale', math.floor((screen_info.current_h * .9) / GameSettings.internal_h))

    GameSettings.scaler = math.floor((screen_info.current_h * .9) / GameSettings.internal_h)
    real_screen = pygame.display.set_mode(get_real_res(), flags)

    return real_screen

def shutdown():
    pygame.quit()
# Stuff outside of my restart loop
######################################

# here we go
def main(real_screen):
    if len(sys.argv) > 1:
        GameSettings.game_scale = int(sys.argv[1])
    screen = pygame.Surface(get_internal_res())
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

    #debug_font = pygame_freetype.Font(None)
    #debug_font.antialiased = False
    #debug_font.fgcolor = (181, 235, 181, 255)
    #debug_font.size = 11
    #debug_text_rect = pygame.Rect(4, 34, 10, 10)

    debug_font_pixel = MonoFont('0123456789', 'outline_numbers', 6, 9, 0)
    debug_text_pixel = MonoText(1, debug_font_pixel, '00')

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

        camera.topleft = camera_follow.get_follow_pos()

        # draw stuff
        screen.blit(background, (0, 0))
        for render_obj in render_list:
            render_obj.render(camera, screen)

        if GameSettings.enable_fps:
            fps = str(math.floor(clock.get_fps()))
            #debug_font.render_to(screen, debug_text_rect, fps)
            debug_text_pixel.set_text(fps)
            screen.blit(debug_text_pixel.image, (4, 4))

        real_screen.blit(pygame.transform.scale(screen, get_real_res()), (0, 0))
        pygame.display.flip()

    return world.restart

# standard python start stuffff
if __name__ == "__main__":
    real_screen = initialize()

    restart = True
    while restart:
        restart = main(real_screen)

    shutdown()
