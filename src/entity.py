import pygame
import math
import yaml
import random

from constants import *
from sprite import BasicSprite
from inventory import Inventory

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

    SCREEN_SLEEP_DISTANCE = 18

    def __init__(self, world, x, y, visible=True, ent_type='creature', subtype='goon'):

        # Figure out which image to use
        self.img_name = 'no_img'
        if ent_type == 'bustable' or ent_type == 'pickup':
            self.img_name = subtype
        elif ent_type == 'door':
            self.img_name = 'door'
        elif ent_type == 'creature':
            creature_spec = {}
            with open('data/creatures.yaml') as creature_data:
                creature_spec = yaml.load(creature_data)[subtype]
            #if GameSettings.debug_mode:
                #print(creature_spec)
            self.img_name = creature_spec['image'] if 'image' in creature_spec else 'no_img'

        # Figure out which layer to use
        layer = 4
        if ent_type == 'pickup':
            layer = 2

        # Create Sprite
        super().__init__(self.img_name, visible, layer)
        self.subtype = subtype

        # Set position on grid
        self.world = world
        self.set_grid_position(x, y)

        self.entity_type = ent_type

        # Default attributes, can be overriden by creature spec
        self.living = True
        self.hidden = True
        self.hp = 1
        self.base_attack = 1
        self.has_inventory = False

        self.moves = False
        self.animates = False

        # Special defaults
        if ent_type == 'bustable':
            self.drops = [{'type': 'pickup', 'subtype': 'moni'}]
        elif ent_type == 'creature':
            self.moves = True
            self.animates = True
        elif ent_type == 'door':
            self.closed = True

        if self.moves:
            self.move_wait = 0
            self.can_diagonal = False
            self.friendly_fire = False
            self.movement_pattern = "naive"

        if ent_type == 'creature':
            if 'loot' in creature_spec:
                self.drops = creature_spec['loot']
            if 'attributes' in creature_spec:
                for attr, val in creature_spec['attributes'].items():
                    setattr(self, attr, val)

        # Automatic attributes
        if self.moves:
            self.active = not self.hidden
            self.wait_counter = self.move_wait
            self.prefer_horizontal = True

        if self.animates:
            # Should be facing right when unflipped
            self.img_flipped = False

            px, py = self.get_pos()
            self.origin_pos_x = px
            self.origin_pos_y = py
            self.target_pos_x = px
            self.target_pos_y = py

            self.anim_bounce = False
            self.non_move_animation = False

        if self.has_inventory:
            self.inventory = Inventory()

    def get_grid_x_y(self):
        return self.grid_x, self.grid_y

    def relative_move(self, x_delta, y_delta):
        self.set_grid_position(self.grid_x + x_delta, self.grid_y + y_delta, not self.animates)

    def set_grid_position(self, x, y, instant_move=True):
        self.grid_x = x
        self.grid_y = y
        if instant_move or not self.animates:
            self.set_pos(x * GRID_WIDTH, y * GRID_WIDTH)
        else:
            self.animate_to(x * GRID_WIDTH, y * GRID_WIDTH, False)

    ##############################
    # Combat, AI, Visibility etc
    def get_attack(self):
        return {'amount': self.base_attack, 'damage_types': []}

    def take_damage(self, damage):
        self.hp -= damage['amount']

        # Immediately counterattack if still waiting to move
        if hasattr(self, 'wait_counter') and hasattr(self, 'no_wait_on_hit'):
            self.wait_counter = 0

        if self.hp <= 0:
            self.die()

        if self.entity_type == 'creature' and self.subtype == 'player':
            self.world.player_stat_change()
            self.world.do_camera_shake(0.2)

    def reveal(self):
        self.hidden = False
        self.visible = True
        if self.moves:
            self.active = True

    def die(self, enable_drops=True):
        self.kill() # Removes sprite from all groups, if that was the only reference to the entity it will be garbage collected
        self.living = False
        if self.moves:
            self.active = False

        if enable_drops and hasattr(self, 'drops'):
            for drop in self.drops:
                self.world.add_entity_at(self.grid_x, self.grid_y, self.visible, drop['type'], drop['subtype'])

    def sleep(self):
        self.visible = False
        if self.moves:
            self.active = False

    def wake(self):
        self.visible = True
        if self.moves:
            self.active = True

    def do_a_thing(self):
        if not self.moves or not self.living:
            return

        if not self.active:
            if not self.far_offscreen():
                self.wake()
            else:
                return
        elif self.far_offscreen():
            self.sleep()
            return

        if self.entity_type == 'creature':
            if self.wait_counter > 0:
                self.wait_counter -= 1
                return

            if self.movement_pattern == 'chase':
                if self.far_offscreen():
                    print('offscreen as I suspected')
                deltas = self.pathfind_follow_player()
            elif self.movement_pattern == 'naive':
                deltas = self.simple_follow_player()
            elif self.movement_pattern == 'random':
                deltas = self.get_random_move()
            else:
                print("Bad movement pattern: " + str(self.movement_pattern))
                return

            if not deltas:
                return
            delta_x, delta_y = deltas

            if not self.friendly_fire:
                stuff = self.world.what_is_at(self.grid_x + delta_x, self.grid_y + delta_y)
                for e in stuff['entities']:
                    if e.entity_type == 'creature' and e.subtype != 'player':
                        # Friendly Fire! let's not
                        return

            self.world.attempt_move(self, delta_x, delta_y)
            self.wait_counter = self.move_wait

    def get_random_move(self):
        moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        if self.can_diagonal:
            moves.extend([(1, 1), (-1, -1), (1, -1), (-1, 1)])

        open_moves = []
        for dx, dy in moves:
            if self.world.can_move(self, dx, dy):
                open_moves.append((dx, dy))

        if len(open_moves) < 1:
            return False

        return random.choice(open_moves)

    def pathfind_follow_player(self):
        player_x, player_y = self.world.get_player().get_grid_x_y()
        path = self.world.pathfind(self.grid_x, self.grid_y, player_x, player_y)
        if not path:
            return False
        # Follow the first delta move in the path
        x_delta, y_delta = path[0]

        # orthogal move or we can move diagonally
        if self.can_diagonal or x_delta == 0 or y_delta == 0:
            return (x_delta, y_delta)

        # diagonal move we need to translate to orthogonal
        self.prefer_horizontal = not self.prefer_horizontal
        if self.prefer_horizontal:
            return (x_delta, 0)
        else:
            return (0, y_delta)

    def simple_follow_player(self):
        player_x, player_y = self.world.get_player().get_grid_x_y()
        x_diff = player_x - self.grid_x
        y_diff = player_y - self.grid_y

        horizontal = (int(math.copysign(1, x_diff)), 0)
        vertical = (0, int(math.copysign(1, y_diff)))
        if abs(x_diff) == abs(y_diff):
            self.prefer_horizontal = not self.prefer_horizontal
            return horizontal if self.prefer_horizontal else vertical
        else:
            return horizontal if abs(x_diff) > abs(y_diff) else vertical

    def far_offscreen(self):
        player_x, player_y = self.world.get_player().get_grid_x_y()
        x_diff = abs(player_x - self.grid_x)
        y_diff = abs(player_y - self.grid_y)

        return max(x_diff, y_diff) > Entity.SCREEN_SLEEP_DISTANCE
    # Combat, AI, Visibility etc
    #################################

    ########################
    # Animation functions
    def get_follow_pos(self):
        if self.non_move_animation:
            return (self.origin_pos_x, self.origin_pos_y)
        else:
            return self.get_pos()

    def change_look(self, left=True):
        if self.img_flipped != left:
            self.image = pygame.transform.flip(self.image, True, False)
        self.img_flipped = left

    def animate_to(self, x, y, bounce):
        # Animate from current position
        ox, oy = self.get_pos()
        self.origin_pos_x = ox
        self.origin_pos_y = oy

        self.target_pos_x = x
        self.target_pos_y = y
        self.anim_bounce = bounce

        # Look left or right
        if ox != x:
            self.change_look(ox-x > 0)
        self.non_move_animation = False

    def no_anim(self):
        ox, oy = self.get_pos()
        self.origin_pos_x = ox
        self.origin_pos_y = oy
        self.target_pos_x = ox
        self.target_pos_y = oy
        self.non_move_animation = False
    
    def bump_animation(self, dx, dy):
        px, py = self.get_pos()
        self.animate_to(px + (dx * Entity.bump_constant), py + (dy * Entity.bump_constant), True)
        self.non_move_animation = True

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
    # Animation functions
    ##################################3

