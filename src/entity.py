import pygame
import math

from sprite import BasicSprite

GRID_WIDTH = 14

def int_bounce_tween(from_v, to_v, progress):
    # double the distance because I'm making progress go 0 -> .5 -> 0
    diff = (to_v - from_v) * 2
    if progress > .5:
        progress = 1.0 - progress
    return from_v + round(diff * progress)

def int_tween(from_v, to_v, progress):
    diff = to_v - from_v
    return from_v + round(diff * progress)

class Entity(BasicSprite):
    bump_constant = 5
    bump_progress_multiplier = 2.0

    def __init__(self, world, x, y, visible=True, img_name='dude', ent_type='creature', layer = 0):
        super().__init__(img_name, visible, layer)

        self.world = world
        self.set_grid_position(x, y)
        self.entity_type = ent_type

        self.living = True
        self.hp = 1
        self.base_attack = 1

        if ent_type == 'creature' and img_name == 'goon':
            self.drops = [{'type': 'pickup', 'image': 'moni'}]
        if ent_type == 'creature' and img_name == 'eyepod':
            self.drops = [{'type': 'pickup', 'image': 'moni_pile'}]
            self.hp = 4
            self.base_attack = 7

        if ent_type == 'bustable':
            self.drops = [{'type': 'pickup', 'image': 'moni'}]

        self.moves = True if ent_type == 'creature' else False
        self.animates = self.moves
        if self.moves:
            self.active = visible

            px, py = self.get_pos()
            self.origin_pos_x = px
            self.origin_pos_y = py
            self.target_pos_x = px
            self.target_pos_y = py

            self.anim_bounce = False

    def get_attack(self):
        return {'amount': self.base_attack, 'damage_types': []}

    def take_damage(self, damage):
        self.hp -= damage['amount']
        if self.hp <= 0:
            self.die()

    def reveal(self):
        self.visible = True
        if self.moves:
            self.active = True

    def do_a_thing(self):
        if self.entity_type == 'creature':
            player_x, player_y = self.world.get_player().get_grid_x_y()

            x_diff = player_x - self.grid_x
            y_diff = player_y - self.grid_y

            if abs(x_diff) >= abs(y_diff):
                self.world.attempt_move(self, math.copysign(1, x_diff), 0)
            else:
                self.world.attempt_move(self, 0, math.copysign(1, y_diff))

    def die(self, enable_drops=True):
        self.kill()
        self.living = False
        if self.moves:
            self.active = False

        if enable_drops and hasattr(self, 'drops'):
            for drop in self.drops:
                self.world.add_entity_at(self.grid_x, self.grid_y, True, drop['type'], drop['image'])

    def animate_to(self, x, y, bounce):
        self.target_pos_x = x
        self.target_pos_y = y
        self.anim_bounce = bounce

        self.reset_anim_origin()

    def reset_anim_origin(self):
        ox, oy = self.get_pos()
        self.origin_pos_x = ox
        self.origin_pos_y = oy

    def set_grid_position(self, x, y, instant_move=True):
        self.grid_x = x
        self.grid_y = y
        if instant_move:
            self.set_pos(x * GRID_WIDTH, y * GRID_WIDTH)
        else:
            self.animate_to(x * GRID_WIDTH, y * GRID_WIDTH, False)
    
    def bump_animation(self, dx, dy):
        px, py = self.get_pos()
        self.animate_to(px + (dx * Entity.bump_constant), py + (dy * Entity.bump_constant), True)

    def get_grid_x_y(self):
        return self.grid_x, self.grid_y

    def relative_move(self, x_delta, y_delta):
        self.set_grid_position(self.grid_x + x_delta, self.grid_y + y_delta, not self.animates)

    def animate_update(self, progress):
        if self.anim_bounce:
            progress *= Entity.bump_progress_multiplier
            progress = min(1.0, progress)
            new_x = int_bounce_tween(self.origin_pos_x, self.target_pos_x, progress)
            new_y = int_bounce_tween(self.origin_pos_y, self.target_pos_y, progress)
        else:
            new_x = int_tween(self.origin_pos_x, self.target_pos_x, progress)
            new_y = int_tween(self.origin_pos_y, self.target_pos_y, progress)
        self.set_pos(new_x, new_y)

