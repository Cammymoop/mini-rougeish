import pygame
import math
from pygame.locals import *

from sprite import BasicSprite, load_png_image

class MonoText(BasicSprite):
    def __init__(self, layer, mono_font, text='', align='left'):
        self.font = mono_font
        self.text = text
        self.text_dirty = True
        self.old_len = 0
        self.align = align

        super().__init__('no_img', True, layer)
        self.self_draw()

    def set_text(self, text, redraw=True):
        self.text = text
        self.text_dirty = True
        if redraw:
            self.self_draw()

    def set_tr_pos(self, x, y):
        if self.text_dirty:
            self.self_draw()
        x -= self.rect.width
        self.set_tl_pos(x, y)

    def update_size(self):
        total_len = len(self.text)
        if total_len == 0:
            self.make_img(self.font.char_width, self.font.char_height)
        else:
            width = self.font.char_width * total_len
            width += self.font.spacing_h * (total_len - 1)
            self.make_img(width, self.font.char_height)

    def self_draw(self, amount=1):
        render_length = 0
        total_len = len(self.text)
        if total_len > 0:
            render_length = min(total_len, math.ceil(total_len * amount))

        # resize own surface if necessary
        if self.text_dirty:
            self.text_dirty = False
            if self.old_len != total_len:
                self.update_size()
            self.old_len = total_len

        self.image.fill(pygame.Color(0, 0, 0, 0))
        if amount < 1:
            start_x = 0
            if self.align == 'right':
                start_x = self.rect.width - (self.font.char_width * render_length) - max(0, self.font.spacing_h * (render_length - 1))

            txt_slice = self.text[-render_length:] if self.align == 'right' else self.text[:render_length]
            self.font.draw_chars(txt_slice, self.image, (start_x, 0))
        else:
            self.font.draw_chars(self.text, self.image, (0, 0))

class MonoFont:
    def __init__(self, characters, img_name, w, h, spacing=0, v_spacing=1):
        self.characters = characters

        self.surface, self.rect = load_png_image(img_name)

        self.char_width = w
        self.char_height = h
        self.spacing_h = spacing
        self.spacing_v = v_spacing

    # draw characters in a single line to the passed surface
    def draw_chars(self, chars, destination_surface, destination_start):
        dest_x, dest_y = destination_start
        for char in chars:
            char_index = self.characters.find(char)
            if char_index == -1:
                char_index = 4 # Show a 4 if can't find the character
            src_area = pygame.Rect(char_index * self.char_width, 0, self.char_width, self.char_height)
            destination_surface.blit(self.surface, (dest_x, dest_y), src_area)

            dest_x += self.char_width + self.spacing_h

