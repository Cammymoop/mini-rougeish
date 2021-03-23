import os, sys
import pygame

from pygame.locals import *

def load_png_image(name):
    path = os.path.join('assets', 'img', name + '.png')
    img_surface = pygame.image.load(path)
    img_surface = img_surface.convert_alpha()
    return img_surface, img_surface.get_rect()

class BasicSprite(pygame.sprite.Sprite):
    def __init__(self, img_name='floor'):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = load_png_image(img_name)
        self.base_width = self.rect.width
        self.base_height = self.rect.height

    def set_pos(self, x, y):
        self.rect.center = (x, y)


# here we go
def main():
    pygame.init()
    flags = 0 # to set full screen use FULLSCREEN instead of 0
    real_screen = pygame.display.set_mode((800, 600), flags)
    screen = pygame.Surface((200, 150))
    screen = screen.convert()

    pygame.display.set_caption("Urg")

    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((8, 20, 30))

    screen.blit(background, (0, 0))

    sprites = pygame.sprite.Group()

    x_start = 100
    y_start = 40
    for i in range(4):
        for j in range(4):
            sp = BasicSprite('floor')
            sp.set_pos(x_start + (i * 14), y_start + (j * 14))
            sprites.add(sp)

    sprites.draw(screen)
    pygame.display.flip()

    clock = pygame.time.Clock()

    # game loop
    running = True
    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                running = False

        # draw stuff
        screen.blit(background, (0, 0))
        sprites.draw(screen)

        real_screen.blit(pygame.transform.scale(screen, (800, 600)), (0, 0))
        pygame.display.flip()

    pygame.quit()

# standard python start stuffff
if __name__ == "__main__":
    main()
