from pygame.locals import *

from constants import *
from sprite import BasicSprite
from text import MonoFont, MonoText

class InventoryMenu:
    def __init__(self, input_manager, sprite_group, inventory):
        self.input_manager = input_manager
        self.sprite_group = sprite_group
        self.sprites = []

        self.rows = 3
        self.cols = 3

        self.inventory = inventory
        self.cursor_index = 0
        self.cursor_sprite = BasicSprite('inv_cursor', True, 5)
        self.sprite_group.add(self.cursor_sprite)

        self.font = MonoFont('0123456789', 'outline_numbers', 6, 9)

        self.cursor_enabled = True

        self.refresh_display()
        self.visible = True

        self.button_right = self.input_manager.make_button('inv-right', 'inventory', [K_RIGHT, K_d], lambda: self.move_cursor(1, 0))
        self.button_left  = self.input_manager.make_button('inv-left', 'inventory', [K_LEFT, K_a], lambda: self.move_cursor(-1, 0))
        self.button_up    = self.input_manager.make_button('inv-up', 'inventory', [K_UP, K_w], lambda: self.move_cursor(0, -1))
        self.button_down  = self.input_manager.make_button('inv-down', 'inventory', [K_DOWN, K_s], lambda: self.move_cursor(0, 1))

        self.button_select = self.input_manager.make_button('inv-select', 'inventory', [K_SPACE], lambda: self.hide())
        self.button_exit   = self.input_manager.make_button('inv-exit', 'inventory', [K_ESCAPE], lambda: self.hide())

    def clear_sprites(self):
        for s in self.sprites:
            s.kill()
        self.sprites = []

    def slot_position(self, index):
        c_x, c_y = get_screen_center()

        tl_x = round(c_x - GRID_WIDTH * ((self.cols/2) - .5))
        tl_y = round(c_y - GRID_WIDTH * ((self.rows/2) - .5))

        if index != 'all':
            return (tl_x + ((index % self.cols) * GRID_WIDTH), tl_y + ((index // self.cols) * GRID_WIDTH))

        ret = []
        for i in range(self.inventory.size):
            ret.append((tl_x + ((i % self.cols) * GRID_WIDTH), tl_y + ((i // self.cols) * GRID_WIDTH)))
        return ret

    def refresh_display(self):
        self.clear_sprites()

        slot_positions = self.slot_position('all')
        for sx, sy in slot_positions:
            spr = BasicSprite('inv_slot')
            spr.set_pos(sx, sy)
            self.sprites.append(spr)
            self.sprite_group.add(spr)

        for index, item_name in enumerate(self.inventory.sorted):
            item = self.inventory.items[item_name]
            spr = BasicSprite(item.icon, True, 1)

            pos_x, pos_y = slot_positions[index]
            spr.set_pos(pos_x, pos_y)
            self.sprites.append(spr)
            self.sprite_group.add(spr)

            if item.quantity > 1:
                text = MonoText(6, self.font, str(item.quantity), 'right')
                text.set_tr_pos(pos_x + 9, pos_y + 1)
                self.sprites.append(text)
                self.sprite_group.add(text)

        cursor_x, cursor_y = slot_positions[self.cursor_index]
        self.cursor_sprite.set_pos(cursor_x, cursor_y)
        if len(self.inventory.items) > 0:
            self.cursor_enabled = True
        else:
            self.cursor_enabled = False

    def move_cursor(self, x, y):
        x_min = (self.cursor_index // self.cols) * self.cols
        x_max = x_min + (self.cols - 1)
        self.cursor_index = max(min(x_max, self.cursor_index + x), x_min)

        y_min = self.cursor_index % self.cols
        y_max = self.cursor_index % self.cols + (self.cols * (self.rows - 1))
        self.cursor_index = max(min(y_max, self.cursor_index + (y * self.cols)), y_min)

        px, py = self.slot_position(self.cursor_index)
        self.cursor_sprite.set_pos(px, py)

    def show(self):
        self.visible = True
        for s in self.sprites:
            s.visible = True

        self.refresh_display()
        if self.cursor_enabled:
            self.cursor_sprite.visible = True

    def hide(self):
        self.visible = False
        self.cursor_sprite.visible = False
        for s in self.sprites:
            s.visible = False
        self.input_manager.focus('game')

