import os
import pygame

def load_png_image(name):
    path = os.path.join('assets', 'img', name + '.png')
    img_surface = pygame.image.load(path)
    img_surface = img_surface.convert_alpha()
    return img_surface, img_surface.get_rect()


class BasicSprite(pygame.sprite.Sprite):
    def __init__(self, img_name='floor', visible=True, layer = 0):
        super().__init__()
        self.image, self.rect = load_png_image(img_name)
        self.layer = layer

        self.visible = visible

    def set_pos(self, x, y):
        self.rect.center = (x, y)

    def get_pos(self):
        return self.rect.center
