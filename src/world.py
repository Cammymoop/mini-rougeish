import pygame
from pygame.locals import *
from constants import *

import collections
import heapq

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
        self.player = Entity(self, 0, 0, True, 'creature', 'player')
        #self.player.moves = False
        #self.player.hp = 8
        self.entity_group.add(self.player)

        self.move_que = collections.deque()
        self.animating = False
        self.animation_length = 112
        self.current_anim_time = 0
        self.max_qued_moves = 2

        self.pathfinding_map = []
        self.pf_offset_x = 0
        self.pf_offset_y = 0
        #self.update_whole_pathfinding_map()

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
                elif event.key == K_LEFT:
                    self.que_move(-1, 0)
                elif event.key == K_DOWN:
                    self.que_move(0, 1)
                elif event.key == K_UP:
                    self.que_move(0, -1)
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
                        entity.no_anim()

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
        dx, dy = self.move_que.popleft()
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

        # Update the pathfinding map for the node we moved from and moved to
        self.update_pathfinding_node(ex, ey)
        self.update_pathfinding_node(ex + xdelta, ey + ydelta)

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

                if self.pathfinding_map[pf_x][pf_y] == 0:
                    count_nodes += 1

        #print("Updated pathfinding map, " + str(count_nodes) + " traversable nodes")
        #print("Also " + str(hidden_tiles) + " hidden spaces")
        #print("And " + str(skipped) + " skipped out of " + str(total) + ", " + str(total - skipped) + " checked")

    # Dont call with coordinates in an unloaded chunk
    def update_pathfinding_node(self, world_x, world_y):
        pf_x, pf_y = (world_x + self.pf_offset_x, world_y + self.pf_offset_y)

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

        dest_x, dest_y = (dest_x + self.pf_offset_x, dest_y + self.pf_offset_y)
        dest = (dest_x, dest_y)

        def heuristic(coord):
            x, y = coord
            return abs(x - dest_x) + abs(y - dest_y)

        def adjacents(coord):
            x, y = coord
            return [((1, 0), (x + 1, y)), ((0, -1), (x, y - 1)), ((-1, 0), (x - 1, y)), ((0, 1), (x, y + 1))]

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
            next_cost = node_cost[cur] + 1
            for delta, adj in adjacents(cur):
                val = self.pathfinding_map[adj[0]][adj[1]]
                if val > strength:
                    print("wall or something")
                    print(adj)
                    print(start)
                    continue
                if adj in node_cost and node_cost[adj] <= next_cost:
                    print("already check from shorter distance")
                    continue
                node_cost[adj] = next_cost
                priority = next_cost + heuristic(adj)
                heapq.heappush(frontier, (priority, adj))
                delta_from[adj] = delta
                position_from[adj] = cur

        if not path_found:
            print("Could not find path, " + str(len(node_cost)) + " nodes checked")
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

    def chunk_exists_at(self, x, y):
        _, _, cx, cy = self.translate_chunk_coords(x, y)
        return self.chunk_exists(cx, cy)

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
