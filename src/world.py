import pygame
from pygame.locals import *
from constants import *

from sprite import BasicSprite
from offset import OffsetGroup
from entity import Entity
from tilemap import TileMap

from generation import generate_chunk

import random

class GameWorld:
    def __init__(self, clock):
        self.clock = clock
        random.seed()

        self.restart = False

        self.render_list = []

        self.maps = {0: {}}

        self.entity_group = OffsetGroup()
        offset_x, offset_y = get_screen_center_offset()
        self.entity_group.set_camera_offset(offset_x, offset_y)

        generate_chunk(self, 0, 0)

        self.clear_entities_at(0, 0)
        self.player = Entity(self, 0, 0, True, 'dude', 'creature', 5)
        self.player.moves = False
        self.player.hp = 8
        self.entity_group.add(self.player)

        self.move_que = []
        self.animating = False
        self.animation_length = 112
        self.current_anim_time = 0
        self.max_qued_moves = 2

        # Reveal the room where the player starts
        self.reveal(0, 0)

    def update(self):
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return False
                elif event.key == K_d:
                    GameSettings.enable_fps = not GameSettings.enable_fps
                elif event.key == K_r:
                    self.restart = True
                    return False
                elif event.key == K_RIGHT:
                    self.que_move(1, 0)
                    #self.attempt_move(self.player, 1, 0)
                elif event.key == K_LEFT:
                    self.que_move(-1, 0)
                    #self.attempt_move(self.player, -1, 0)
                elif event.key == K_DOWN:
                    self.que_move(0, 1)
                    #self.attempt_move(self.player, 0, 1)
                elif event.key == K_UP:
                    self.que_move(0, -1)
                    #self.attempt_move(self.player, 0, -1)
                elif event.key == K_SPACE:
                    if not self.animating:
                        self.time_advance()
                        self.animating = True

        if self.animating:
            tick_length = self.clock.get_time()
            self.current_anim_time += tick_length

            anim_progress = self.current_anim_time / self.animation_length
            anim_progress = min(1.0, anim_progress)
            for entity in self.entity_group.sprites():
                if entity.animates and entity.active:
                    entity.animate_update(anim_progress)

            if anim_progress == 1.0:
                self.animating = False 
                self.current_anim_time = 0
                for entity in self.entity_group.sprites():
                    if entity.animates and entity.active:
                        entity.reset_anim_origin()

                if self.player == entity:
                    self.after_player_move()

        if not self.animating and len(self.move_que) > 0:
            self.handle_move_que()

        return True

    def time_advance(self):
        for e in self.entity_group.sprites():
            if e.moves and e.active:
                e.do_a_thing()


    def get_player(self):
        return self.player

    def handle_move_que(self):
        if not self.player.living:
            return
        dx, dy = self.move_que.pop(0)
        self.attempt_move(self.player, dx, dy)

        self.time_advance()
        self.animating = True

    def que_move(self, xdelta, ydelta):
        if len(self.move_que) < self.max_qued_moves:
            self.move_que.append((xdelta, ydelta))

    def attempt_move(self, entity, xdelta, ydelta):
        ex, ey = entity.get_grid_x_y()
        target_stuff = self.what_is_at(ex + xdelta, ey + ydelta)
        if not target_stuff['tile']:
            return False

        targetable_types = ['creature', 'bustable']

        for e in target_stuff['entities']:
            if e.entity_type == 'door' and self.player == entity:
                e.visible = False # A bit hacky, I want to reveal after move completes, but hide the door when move starts
            if e.entity_type not in targetable_types:
                continue

            e.take_damage(entity.get_attack())
            entity.bump_animation(xdelta, ydelta)
            return False
        
        # Now actually move if we didn't bump something
        entity.relative_move(xdelta, ydelta)

    def after_player_move(self):
        px, py = self.player.get_grid_x_y()
        stuff_here = self.what_is_at(px, py)

        for e in stuff_here['entities']:
            if e.entity_type == 'door' and e.closed:
                e.closed = False
                e.visible = False
                self.reveal(px, py)
            elif e.entity_type == 'pickup':
                # TODO inventory!!!!
                e.take_damage({'amount': 999})

    def what_is_at(self, x, y):
        # Return tile info and whatever entities are at a tile position
        in_chunk_x, in_chunk_y, chunk_x, chunk_y = self.translate_chunk_coords(x, y)
        ret = {'tile': self.get_tile_from_world_coord(x, y)}

        entities_here = []
        for e in self.entity_group.sprites():
            ex, ey = e.get_grid_x_y()
            if ex == x and ey == y:
                entities_here.append(e)

        ret['entities']= entities_here
        return ret
    
    # reveal a tile and all connected hidden tiles including entities on them
    # stop spreading the reveal if you hit a door or a non hidden tile
    def reveal(self, x, y):
        to_check = set([(x, y)])
        checked = set([])

        adjacents = [(-1, 0), (0, -1), (1, 0), (0, 1)]

        infinity_protection = 200
        while len(to_check) > 0:
            for px, py in to_check.copy():
                # Show everything here
                stuff_here = self.what_is_at(px, py)
                stuff_here['tile'].visible = True

                stop_here = False
                for e in stuff_here['entities']:
                    e.reveal()
                    # If there's a closed door stop checking adjacent tiles
                    if e.entity_type == 'door':
                        if e.closed:
                            #print('Hit closed door')
                            stop_here = True
                        else:
                            e.visible = False

                checked.add((px, py))

                if not stop_here:
                    # Check all adjecent tiles for hidden tiles to show
                    for dx, dy in adjacents:
                        nx, ny = (px + dx, py + dy)
                        # Skip already checked tiles or ones already in the to-check list
                        if (nx, ny) in checked or (nx, ny) in to_check:
                            continue

                        stuff = self.what_is_at(nx, ny)
                        # Skip 
                        if not stuff['tile'] or stuff['tile'].visible:
                            continue

                        # Ok so this is a hidden tile, add it to the list
                        to_check.add((nx, ny))

                to_check.remove((px, py))

            infinity_protection -= 1
            if infinity_protection < 0:
                print("Infinite loop in world.reveal()!")
                return
                

    def get_tile_from_world_coord(self, x, y):
        in_chunk_x, in_chunk_y, chunk_x, chunk_y = self.translate_chunk_coords(x, y)
        if self.chunk_exists(chunk_x, chunk_y):
            return self.maps[chunk_y][chunk_x].get_tile(in_chunk_x, in_chunk_y)
        else:
            return False

    def chunk_exists(self, chunk_x, chunk_y):
        if chunk_y not in self.maps or chunk_x not in self.maps[chunk_y]:
            return False
        return True

    # translate world x, y -> in_chunk_x, in_chunk_y, chunk_x, chunk_y
    def translate_chunk_coords(self, x, y):
        return x % TM_CHUNK_SIZE, y % TM_CHUNK_SIZE, x // TM_CHUNK_SIZE, y // TM_CHUNK_SIZE

    def update_render_list(self):
        self.render_list = []
        for row in self.maps.keys():
            for t_map in self.maps[row].values():
                self.render_list.append(t_map)

    def render(self, camera, surface):
        for t_map in self.render_list:
            t_map.render(camera, surface)

        self.entity_group.render(camera, surface)

    def add_chunk(self, chunk_x, chunk_y, chunk):
        self.maps[chunk_y][chunk_x] = chunk
        self.update_render_list()

    def add_entity_at(self, x, y, visible, entity_type, image_name):
        layer = 4
        if entity_type == 'pickup':
            layer = 1
        e = Entity(self, x, y, visible, image_name, entity_type, layer)
        self.entity_group.add(e)
        return e

    def clear_entities_at(self, x, y):
        stuff = self.what_is_at(x, y)

        for e in stuff['entities']:
            if e.living:
                e.die(False)

            self.entity_group.remove(e)
