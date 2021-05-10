import os
import pygame
from pygame.locals import *

def load_png_image(name):
    # should probably cache image surfaces
    # if I do I need to cache flipped versions too as blitting doesn't support flipping itself
    path = os.path.join('assets', 'img', name + '.png')
    img_surface = pygame.image.load(path)
    img_surface = img_surface.convert_alpha()
    return img_surface, img_surface.get_rect()


class BasicSprite(pygame.sprite.Sprite):
    def __init__(self, img_name='no_img', visible=True, layer=0):
        super().__init__()
        self.load_img(img_name)
        self.layer = layer

        self.visible = visible

    def load_img(self, img_name):
        self.image, self.rect = load_png_image(img_name)

    def make_img(self, w, h):
        self.image = pygame.Surface((w, h), SRCALPHA)
        self.rect = self.image.get_rect()

    def set_tl_pos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def set_pos(self, x, y):
        self.rect.center = (x, y)

    def get_pos(self):
        return self.rect.center
