import pygame
from pygame.locals import *
from constants import *

import math
import collections
import heapq

from sprite import BasicSprite
from offset import OffsetGroup
from entity import Entity
from tilemap import TileMap
from sprite import BasicSprite
from inventory import Item, Inventory, item_from_pickup
from inventory_menu import InventoryMenu
from input_manager import InputManager

from generation import generate_chunk, generate_floor

import random

class GameWorld:
    def __init__(self, clock):
        self.clock = clock
        random.seed()

        self.restart = False

        self.render_list = []

        self.maps = {0: {}}

        # If this entity group fills up with too many entities (a really big floor) it may cause performance problems
        # not worrying about it for now but might make a deactivated entity group or something
        self.entity_group = OffsetGroup()
        offset_x, offset_y = get_screen_center_offset()
        self.entity_group.set_camera_offset(offset_x, offset_y)

        self.ui_group = OffsetGroup()

        self.floor_data = generate_floor()
        self.starting_chunk = self.floor_data['starting-chunk']
        if GameSettings.debug_mode:
            for chunk in self.floor_data['chunks']:
                generate_chunk(self, self.floor_data, self.floor_data['chunk-properties'][chunk])
        else:
            generate_chunk(self, self.floor_data, self.floor_data['chunk-properties'][self.starting_chunk])

        chunk_spawn_x, chunk_spawn_y = self.floor_data['spawn']
        start_x, start_y = self.chunk_coord_to_world_coord(self.floor_data['starting-chunk'], chunk_spawn_x, chunk_spawn_y)

        self.clear_entities_at(start_x, start_y)
        self.player = Entity(self, start_x, start_y, True, 'creature', 'player')
        self.entity_group.add(self.player)

        scr_width = get_internal_res()[0]
        blip_x = scr_width - 8
        blip_y = 8 + ((self.player.hp-1) * 5)
        self.health_blips = []
        for i in range(self.player.hp):
            spr = BasicSprite('blip', True, 20)
            spr.set_pos(blip_x, blip_y - (5 * i))
            self.ui_group.add(spr)
            self.health_blips.append(spr)

        self.move_que = collections.deque()
        self.animating = False
        self.animation_length = 112
        self.current_anim_time = 0
        self.max_qued_moves = 2

        self.pathfinding_map = []
        self.pf_offset_x = 0
        self.pf_offset_y = 0

        self.cam_shake_intensity = 4
        self.cam_shake_countdown = 0

        self.keyboard_focus = 'game'

        self.input_manager = InputManager()
        self.input_manager.focus('game')

        self.button_right = self.input_manager.make_button('right', 'game', [K_RIGHT, K_d], lambda: self.que_move(1, 0), True)
        self.button_left  = self.input_manager.make_button('left', 'game', [K_LEFT, K_a], lambda: self.que_move(-1, 0), True)
        self.button_up    = self.input_manager.make_button('up', 'game', [K_UP, K_w], lambda: self.que_move(0, -1), True)
        self.button_down  = self.input_manager.make_button('down', 'game', [K_DOWN, K_s], lambda: self.que_move(0, 1), True)

        self.exit_next = False
        def c_exit():
            self.exit_next = True
        self.button_exit  = self.input_manager.make_button('exit', 'game', [K_ESCAPE], c_exit)
        self.reset_next = False
        def c_reset():
            self.reset_next = True
        self.button_exit  = self.input_manager.make_button('reset', False, [K_r], c_reset)

        self.button_menu  = self.input_manager.make_button('menu', False, [K_RETURN, K_e], self.inventory_toggle)

        self.inv_display = InventoryMenu(self.input_manager, self.ui_group, self.player.inventory)
        self.inv_display.hide()

        # Reveal the room where the player starts
        self.reveal(start_x, start_y)

    def inventory_toggle(self):
        if self.inv_display.visible:
            self.inv_display.hide()
            self.input_manager.focus('game')
        else:
            self.inv_display.show()
            self.input_manager.focus('inventory')


    def update(self):
        all_events = pygame.event.get()
        self.input_manager.update(all_events, self.clock.get_time())

        if self.exit_next:
            return False
        if self.reset_next:
            self.restart = True
            return False

        for event in all_events:
            if event.type == KEYDOWN:
                if event.key == K_LEFTBRACKET:
                    GameSettings.debug_mode = not GameSettings.debug_mode
                elif event.key == K_p:
                    GameSettings.enable_fps = not GameSettings.enable_fps

                if self.keyboard_focus == 'game':
                    if event.key == K_SPACE:
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
                        entity.no_anim()

                    if self.player == entity:
                        self.after_player_move()

        if not self.animating and len(self.move_que) > 0:
            self.handle_move_que()

        self.cam_shake_update()

        return True

    def delta_time_seconds(self):
        return self.clock.get_time() / 1000
    
    def cam_shake_update(self):
        if self.cam_shake_countdown < 0:
            return
        self.cam_shake_countdown = max(0, self.cam_shake_countdown - self.delta_time_seconds())

    def player_stat_change(self):
        hp = self.player.hp
        for i in range(len(self.health_blips)):
            self.health_blips[i].visible = True if hp > i else False

    def time_advance(self):
        for e in self.entity_group.sprites():
            # Call even if not active so they can wake themselves up
            if e.moves and not e.hidden:
                e.do_a_thing()

    def get_player(self):
        return self.player

    def handle_move_que(self):
        if not self.player.living:
            return
        dx, dy = self.move_que.popleft()
        self.attempt_move(self.player, dx, dy)

        self.time_advance()
        self.animating = True

    def que_move(self, xdelta, ydelta):
        if len(self.move_que) < self.max_qued_moves:
            self.move_que.append((xdelta, ydelta))

    def can_move(self, entity, xdelta, ydelta):
        ex, ey = entity.get_grid_x_y()
        target_stuff = self.what_is_at(ex + xdelta, ey + ydelta)
        if not target_stuff['tile']:
            return False

        # Dont let anyone but the player open doors
        if entity.subtype != 'player':
            for e in target_stuff['entities']:
                if e.entity_type == 'door' and e.closed:
                    return False

        return True

    def attempt_move(self, entity, xdelta, ydelta):
        ex, ey = entity.get_grid_x_y()
        target_stuff = self.what_is_at(ex + xdelta, ey + ydelta)
        if not target_stuff['tile']:
            if not GameSettings.debug_mode or entity != self.player:
                return False

        targetable_types = ['creature', 'bustable']

        for e in target_stuff['entities']:
            if e.entity_type == 'door' and e.closed:
                if self.player == entity:
                    e.visible = False # A bit hacky, I want to reveal after move completes, but hide the door when move starts
                else:
                    return False # Other creatures cant open doors
            if e.entity_type not in targetable_types:
                continue

            e.take_damage(entity.get_attack())

            # update the pathfinding at the target in case it died
            self.update_pathfinding_node(ex + xdelta, ey + ydelta)
            entity.bump_animation(xdelta, ydelta)
            return False
        
        # Now actually move if we didn't bump something
        entity.relative_move(xdelta, ydelta)

        # Update the pathfinding map for the node we moved from and moved to
        self.update_pathfinding_node(ex, ey)
        self.update_pathfinding_node(ex + xdelta, ey + ydelta)

    def after_player_move(self):
        px, py = self.player.get_grid_x_y()
        stuff_here = self.what_is_at(px, py)

        for e in stuff_here['entities']:
            if e.entity_type == 'door':
                e.closed = False
                e.visible = False
                self.reveal(px, py)
            elif e.entity_type == 'pickup':
                pickup_item = item_from_pickup(e)
                if pickup_item:
                    self.player.inventory.add_item(pickup_item)
                e.take_damage({'amount': 999})

        path_center_x = (PATHFINDING_WIDTH//2) - self.pf_offset_x
        path_center_y = (PATHFINDING_HEIGHT//2) - self.pf_offset_y
        if max(abs(px - path_center_x), abs(py - path_center_y)) > PATHFINDING_CENTER_DEADZONE:
            self.update_whole_pathfinding_map()

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

    ####################################################
    #Pathfinding

    # Cread 2d int array for pathfinding with A*
    # Numbers > 0 are obstacles of varying types
    # Higher numbers are "harder" to pathfind through
    # Each pathfind will have a strength, it will consider any number higher than that a wall
    # e.g. strength 0 will only move on blank spaces, strength 3 will also pathfind through breakable objects
    def update_whole_pathfinding_map(self):
        path_center_x, path_center_y = self.player.get_grid_x_y()
        self.pf_offset_x = -(path_center_x - (PATHFINDING_WIDTH//2))
        self.pf_offset_y = -(path_center_y - (PATHFINDING_HEIGHT//2))

        count_nodes = 0
        hidden_tiles = 0
        total = PATHFINDING_WIDTH * PATHFINDING_HEIGHT
        skipped = 0
        # 10 is a wall or outside the loaded chunks
        self.pathfinding_map = []
        for pf_x in range(PATHFINDING_WIDTH):
            self.pathfinding_map.append([0] * PATHFINDING_HEIGHT)
            for pf_y in range(PATHFINDING_HEIGHT):
                world_x, world_y = (pf_x - self.pf_offset_x, pf_y - self.pf_offset_y)
                if not self.chunk_exists_at(world_x, world_y):
                    skipped += 1
                    self.pathfinding_map[pf_x][pf_y] = 10
                    continue

                tile = self.get_tile_from_world_coord(world_x, world_y)
                if not tile or not tile.visible:
                    if tile:
                        hidden_tiles += 1
                    self.pathfinding_map[pf_x][pf_y] = 10
                    continue

                stuff = self.what_is_at(world_x, world_y)
                for entity in stuff['entities']:
                    if entity.entity_type == 'bustable':
                        self.pathfinding_map[pf_x][pf_y] = max(3, self.pathfinding_map[pf_x][pf_y])
                    if entity.entity_type == 'creature':
                        self.pathfinding_map[pf_x][pf_y] = max(5, self.pathfinding_map[pf_x][pf_y])
                    if entity.entity_type == 'door' and entity.closed:
                        self.pathfinding_map[pf_x][pf_y] = max(6, self.pathfinding_map[pf_x][pf_y])

                if self.pathfinding_map[pf_x][pf_y] == 0:
                    count_nodes += 1

        #print("Updated pathfinding map, " + str(count_nodes) + " traversable nodes")
        #print("Also " + str(hidden_tiles) + " hidden spaces")
        #print("And " + str(skipped) + " skipped out of " + str(total) + ", " + str(total - skipped) + " checked")

    # Dont call with coordinates in an unloaded chunk
    def update_pathfinding_node(self, world_x, world_y):
        pf_x, pf_y = (world_x + self.pf_offset_x, world_y + self.pf_offset_y)

        if min(pf_x, pf_y) < 0 or pf_x > PATHFINDING_WIDTH - 1 or pf_y > PATHFINDING_HEIGHT - 1:
            print("Tried to update outside pathfinding space")
            print((world_x, world_y), (pf_x, pf_y))
            return

        tile = self.get_tile_from_world_coord(world_x, world_y)
        if not tile or not tile.visible:
            self.pathfinding_map[pf_x][pf_y] = 10
            return

        self.pathfinding_map[pf_x][pf_y] = 0

        stuff = self.what_is_at(world_x, world_y)
        for entity in stuff['entities']:
            if entity.entity_type == 'bustable':
                self.pathfinding_map[pf_x][pf_y] = max(3, self.pathfinding_map[pf_x][pf_y])
            if entity.entity_type == 'creature':
                self.pathfinding_map[pf_x][pf_y] = max(5, self.pathfinding_map[pf_x][pf_y])

    # Find path
    # if abs_path == True, return list of world coordinates along the path
    # otherwise return list of x, y deltas to follow path
    def pathfind(self, start_x, start_y, dest_x, dest_y, strength=0, abs_path=False):
        start = (start_x + self.pf_offset_x, start_y + self.pf_offset_y)

        def outside_check(coord):
            x, y = coord
            return min(x, y) < 0 or x > PATHFINDING_WIDTH - 1 or y > PATHFINDING_HEIGHT - 1

        if outside_check(start):
            print("Tried to pathfind from outside pathfinding space")
            print((start_x, start_y), start)
            return []
        

        dest_x, dest_y = (dest_x + self.pf_offset_x, dest_y + self.pf_offset_y)
        dest = (dest_x, dest_y)

        def heuristic(coord):
            x, y = coord
            return math.sqrt(pow(x - dest_x, 2) + pow(y - dest_y, 2))

        adjacent_deltas = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                adjacent_deltas.append((dx, dy))

        def delta_add(delta, coord):
            return (delta[0] + coord[0], delta[1] + coord[1])

        def is_diagonal(delta):
            return delta[0] != 0 and delta[1] != 0

        def straights(delta):
            return [(delta[0], 0), (0, delta[1])]
        
        path_found = False

        delta_from = {start: None}
        position_from = {start: None}
        node_cost = {start: 0}
        # priority que items go in the list as: (priority, (x, y))
        frontier = [(0, start)]
        while len(frontier) > 0:
            _, cur = heapq.heappop(frontier)

            if cur == dest:
                path_found = True
                break

            # Always cost 1 to move for now
            old_cost = node_cost[cur]
            next_cost = old_cost + 1
            for delta in adjacent_deltas:
                adj = delta_add(delta, cur)
                if outside_check(adj):
                    continue
                val = self.pathfinding_map[adj[0]][adj[1]]
                # If the node is the destination, ignore strength (attack player)
                if val > strength and adj != dest:
                    continue
                # I'm doing diagonal movement for nice pathing but it needs to be a valid path orthoganally too
                if is_diagonal(delta):
                    available_straights = 2
                    for s_delta in straights(delta):
                        s_val = self.pathfinding_map[cur[0] + s_delta[0]][cur[1] + s_delta[1]]
                        if s_val > strength:
                            available_straights -= 1
                    if available_straights < 1:
                        continue


                if adj in node_cost and node_cost[adj] <= next_cost:
                    continue
                node_cost[adj] = next_cost
                priority = next_cost + heuristic(adj)
                heapq.heappush(frontier, (priority, adj))
                delta_from[adj] = delta
                position_from[adj] = cur

        if not path_found:
            #print("Could not find path, " + str(len(node_cost)) + " nodes checked")
            return False

        def to_world(coord):
            lx, ly = coord
            return (lx - self.pf_offset_x, ly - self.pf_offset_y)

        path = []
        cur_node = dest
        while cur_node != start:
            if abs_path:
                path.append(to_world(cur_node))
            else:
                path.append(delta_from[cur_node])
            cur_node = position_from[cur_node]

        path.reverse()
        return path


    # Pathfinding
    ####################################################

    
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

                        is_new_chunk = self.pending_chunk_exists_at(nx, ny)
                        if is_new_chunk:
                            print('revealing new chunk')
                            _, _, chunk_x, chunk_y = self.translate_chunk_coords(nx, ny)
                            generate_chunk(self, self.floor_data, self.floor_data['chunk-properties'][(chunk_x, chunk_y)])

                        stuff = self.what_is_at(nx, ny)

                        if not stuff['tile'] or stuff['tile'].visible:
                            continue

                        # Ok so this is a hidden tile, add it to the list
                        to_check.add((nx, ny))

                to_check.remove((px, py))

            infinity_protection -= 1
            if infinity_protection < 0:
                print("Infinite loop in world.reveal()!")
                return
            # End while

        # More tiles available for movement
        self.update_whole_pathfinding_map()
                

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

    def pending_chunk_exists(self, chunk_x, chunk_y):
        if not self.chunk_exists(chunk_x, chunk_y):
            if (chunk_x, chunk_y) in self.floor_data['chunks']:
                return True
        return False

    def chunk_exists_at(self, x, y):
        _, _, cx, cy = self.translate_chunk_coords(x, y)
        return self.chunk_exists(cx, cy)

    def pending_chunk_exists_at(self, x, y):
        _, _, cx, cy = self.translate_chunk_coords(x, y)
        return self.pending_chunk_exists(cx, cy)

    # translate world x, y -> in_chunk_x, in_chunk_y, chunk_x, chunk_y
    def translate_chunk_coords(self, x, y):
        return x % TM_CHUNK_SIZE, y % TM_CHUNK_SIZE, x // TM_CHUNK_SIZE, y // TM_CHUNK_SIZE

    def chunk_coord_to_world_coord(self, chunk_pos, in_chunk_x, in_chunk_y):
        chunk_x, chunk_y = chunk_pos
        return (in_chunk_x + (chunk_x * TM_CHUNK_SIZE), in_chunk_y + (chunk_y * TM_CHUNK_SIZE))

    def update_render_list(self):
        self.render_list = []
        for row in self.maps.keys():
            for t_map in self.maps[row].values():
                self.render_list.append(t_map)

    def do_camera_shake(self, length, intensity=4):
        self.cam_shake_intensity = intensity
        self.cam_shake_countdown = length

    def shake_this_camera(self, camera):
        if self.cam_shake_countdown <= 0:
            return camera
        new_cam = camera.copy()
        new_cam.x += random.randint(0, (self.cam_shake_intensity * 2)) - self.cam_shake_intensity
        new_cam.y += random.randint(0, (self.cam_shake_intensity * 2)) - self.cam_shake_intensity
        return new_cam

    def render(self, camera, surface):
        camera = self.shake_this_camera(camera)
        for t_map in self.render_list:
            t_map.render(camera, surface)

        self.entity_group.render(camera, surface)

        ui_camera = self.shake_this_camera(pygame.Rect(0, 0, 10, 10))
        self.ui_group.render(ui_camera, surface)

    def add_chunk(self, chunk_x, chunk_y, chunk):
        if chunk_y not in self.maps:
            self.maps[chunk_y] = {}
        self.maps[chunk_y][chunk_x] = chunk
        self.update_render_list()

    def add_entity_at(self, x, y, visible, entity_type, entity_subtype):
        e = Entity(self, x, y, visible, entity_type, entity_subtype)
        self.entity_group.add(e)
        return e

    def clear_entities_at(self, x, y):
        stuff = self.what_is_at(x, y)

        for e in stuff['entities']:
            if e.living:
                e.die(False)

            self.entity_group.remove(e)
