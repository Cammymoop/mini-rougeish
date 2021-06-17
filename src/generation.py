from constants import *

import random
import math
from tilemap import TileMap

def generate_floor():
    worms = 2
    chunks_per = 4
    chunks = set()
    chunk_properties = {}

    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    chunk_shapes = ['classic', 'huge-rooms', 'outer-loop']
    shape_weights = [5, 2, 1]

    chunk_colors = ['classic', 'rock', 'red']
    color_weights = [9, 5, 2]

    for worm_i in range(worms):
        cur_x = 0
        cur_y = 0

        set_chunks = 0
        while set_chunks < chunks_per:
            chunk_pos = (cur_x, cur_y)
            if chunk_pos not in chunks:
                chunks.add(chunk_pos)

                shape = random.choices(chunk_shapes, weights=shape_weights)[0]
                chunk_properties[chunk_pos] = {'position': chunk_pos, 'shape': shape}
                if shape == 'huge-rooms':
                    chunk_properties[chunk_pos]['max-depth'] = 3
                elif shape == 'outer-loop':
                    ring_width = random.randint(3, 5)
                    chunk_properties[chunk_pos]['ring-start'] = ring_width 
                    chunk_properties[chunk_pos]['ring-stop'] = TM_CHUNK_SIZE - 2 - ring_width 
                set_chunks += 1

                chunk_properties[chunk_pos]['color'] = random.choices(chunk_colors, weights=color_weights)[0]

            xd, yd = random.choice(directions)
            cur_x += xd
            cur_y += yd

    # define inter-chunk door positions
    doors = {}
    for chunk_pos in chunks:
        this_chunk_x, this_chunk_y = chunk_pos

        if (this_chunk_x + 1, this_chunk_y) in chunks:
            doors[(this_chunk_x, this_chunk_y, 'right')] = random.randint(1, TM_CHUNK_SIZE - 3)

        if (this_chunk_x, this_chunk_y + 1) in chunks:
            doors[(this_chunk_x, this_chunk_y, 'down')] = random.randint(1, TM_CHUNK_SIZE - 3)

    ret = {'chunks': chunks, 'chunk-properties': chunk_properties, 'doors': doors}
    ret['starting-chunk'] = random.choice(list(chunks)) 
    ret['spawn'] = (1, 1)
    if chunk_properties[ret['starting-chunk']]['shape'] == 'outer-loop':
        start_pos = chunk_properties[ret['starting-chunk']]['ring-start'] + 2
        ret['spawn'] = (start_pos, start_pos)
    return ret


def generate_chunk(world, floor_data, chunk_properties):
    chunk_pos = chunk_properties['position']
    chunk_x, chunk_y = chunk_pos
    tile_map = TileMap(chunk_x, chunk_y)
    world.add_chunk(chunk_x, chunk_y, tile_map)

    visible = GameSettings.debug_mode

    floor_prefix = chunk_properties['color'] + '_'
    floor_variants = 2

    def floor_tile_img():
        return floor_prefix + 'floor' + str(random.randint(1, floor_variants))

    # Fill whole chunk first
    for x in range(TM_CHUNK_SIZE - 1):
        for y in range(TM_CHUNK_SIZE - 1):
            tile_map.place_tile(x, y, visible, floor_tile_img())


    # chopper settings by chunk shape
    x, y = (0, 0)
    w, h = (TM_CHUNK_SIZE - 1, TM_CHUNK_SIZE - 1)

    # carve out loop
    if chunk_properties['shape'] == 'outer-loop':
        start_pos = chunk_properties['ring-start']
        stop_pos = chunk_properties['ring-stop']
        x, y = (start_pos + 1, start_pos + 1)
        w, h = (stop_pos - start_pos - 1, stop_pos - start_pos - 1)

        for ring_x in range(start_pos, stop_pos + 1):
            tile_map.clear_tile(ring_x, start_pos)
            tile_map.clear_tile(ring_x, stop_pos)
        for ring_y in range(start_pos + 1, stop_pos):
            tile_map.clear_tile(start_pos, ring_y)
            tile_map.clear_tile(stop_pos, ring_y)

        # make a few doors into the inside
        door_pos_h = start_pos + random.randint(1, stop_pos - start_pos - 1)
        door_pos_v = start_pos + random.randint(1, stop_pos - start_pos - 1)

        door_x = random.choice([start_pos, stop_pos])
        door_y = random.choice([start_pos, stop_pos])

        tile_map.place_tile(door_x, door_pos_v, visible, floor_tile_img())
        world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, door_x, door_pos_v)
        world.add_entity_at(world_x, world_y, visible, 'door', 'door')

        tile_map.place_tile(door_pos_h, door_y, visible, floor_tile_img())
        world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, door_pos_h, door_y)
        world.add_entity_at(world_x, world_y, visible, 'door', 'door')

        outer_ring_furnisher(world, chunk_properties, tile_map, start_pos, stop_pos)

    place_doors(world, tile_map, chunk_pos, chunk_properties, floor_data)
    # Chop up vertically and horizontally to create irregular rooms
    recursive_room_chopper(world, tile_map, chunk_properties, floor_data, x, y, w, h, 1)

def recursive_room_chopper(world, tile_map, chunk_properties, floor_data, x, y, w, h, depth):
    done = False
    # infinite recursion protection
    if depth > 25:
        done = True
    if 'max-depth' in chunk_properties and depth > chunk_properties['max-depth']:
        done = True
    # I dont want to make any rooms slimmer than 3 tiles so dont chop any rooms
    # that are less than 7 tiles in either direction
    if w < 7 and h < 7:
        done = True

    # Random chance of not making the room smaller
    # More likely the smaller the room is
    cut_chance = 100
    area = w * h
    if area <= 35:
        cut_chance = 30
    elif area <= 50:
        cut_chance = 70
    elif area <= 100:
        cut_chance = 92

    if random.randint(1, 100) > cut_chance:
        done = True

    if done:
        rectangle_room_furnisher(world, chunk_properties, tile_map, x, y, w, h)
        return

    chunk_pos = chunk_properties['position']

    valid_cut = False

    # Try to cut the room, cant cut right along where a door goes into this room
    cut_tries = 4
    while not valid_cut:
        vertical = True
        if w < h:
            vertical = False
        elif w == h:
            vertical = random.choice([True, False])

        long_side = w if vertical else h
        slice_position = 3 + random.randint(0, long_side - 7)

        short_side = h if vertical else w
        door_position = random.randint(0, short_side - 1)

        valid_cut = True
        #######################
        # Need to check for illegal slice positions that would cut off the door into the room
        # First check against floor_data for inter-chunk doors if up against the top/left edge
        dc_positions = []
        if vertical and y == 0:
            chunk_x, chunk_y = chunk_pos
            key = (chunk_x, chunk_y - 1, 'down')
            if key in floor_data['doors']:
                door_pos = floor_data['doors'][key]
                if x + slice_position == door_pos:
                    valid_cut = False
        elif not vertical and x == 0:
            chunk_x, chunk_y = chunk_pos
            key = (chunk_x - 1, chunk_y, 'down')
            if key in floor_data['doors']:
                door_pos = floor_data['doors'][key]
                if y + slice_position == door_pos:
                    valid_cut = False

        # Now just check for existing tiles at the edges of the cut (doors already placed in this chunk)
        if vertical:
            dc_x = x + slice_position
            dc_y1 = y - 1
            dc_y2 = y + short_side
            dc_positions = [(dc_x, dc_y1), (dc_x, dc_y2)]
        else:
            dc_y = y + slice_position
            dc_x1 = x - 1
            dc_x2 = x + short_side
            dc_positions = [(dc_x1, dc_y), (dc_x2, dc_y)]

        # Door could be in an adjacent chunk so check it properly
        for door_check_x, door_check_y in dc_positions:
            world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, door_check_x, door_check_y)
            stuff = world.what_is_at(world_x, world_y)
            if stuff['tile']:
                # theres some tile in the wall, I can assume theres a door there
                #print("Stopped an invalid cut")
                valid_cut = False
        # Door check done
        #######################

        cut_tries -= 1
        if cut_tries < 0:
            # couldn't get a valid cut in a few tries so we'll just not cut this room any further
            rectangle_room_furnisher(world, chunk_properties, tile_map, x, y, w, h)
            return
        # End while not valid_cut


    # Cut out the wall
    for i in range(short_side):
        vx, vy = x, y
        vx += slice_position if vertical else i
        vy += i if vertical else slice_position
        if i == door_position:
            # Chance to place closed door
            if random.randint(1, 6) < 6:
                visible = GameSettings.debug_mode

                world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, vx, vy)
                door = world.add_entity_at(world_x, world_y, visible, 'door', 'door')
        else:
            tile_map.clear_tile(vx, vy)

    # Recurse
    if vertical:
        recursive_room_chopper(world, tile_map, chunk_properties, floor_data, x, y, slice_position, h, depth + 1)
        recursive_room_chopper(world, tile_map, chunk_properties, floor_data, x + slice_position + 1, y, w - 1 - slice_position, h, depth + 1)
    else:
        recursive_room_chopper(world, tile_map, chunk_properties, floor_data, x, y, w, slice_position, depth + 1)
        recursive_room_chopper(world, tile_map, chunk_properties, floor_data, x, y + slice_position + 1, w, h - 1 - slice_position, depth + 1)

def rectangle_room_furnisher(world, chunk_properties, tile_map, x, y, w, h):
    all_tiles = set()

    for i in range(x, x + w):
        for j in range(y, y + h):
            all_tiles.add((i, j))

    area = w * h
    min_length = min(w, h)

    if min_length > 6 and area > 84:
        supports_chance = 80
        if area > 100:
            supports_chance = 95

        if random.randint(1, 100) <= supports_chance:
            # cut out some tiles in the middle like they are pillars supporting the ceiling
            vertical = h > w

            # wide pillars if room is even in width
            long_s = (h if vertical else w)
            short_s = (w if vertical else h)

            center_wide = short_s % 2 == 0
            middle = math.floor((short_s / 2) - .5)

            divisions = max(2, math.ceil(long_s / 6))
            spacing = long_s / divisions

            def flipped(coord):
                return (coord[1], coord[0])
            def offset(coord):
                return (coord[0] + x, coord[1] + y)

            pillar_shape = random.choice(['square', '+', '-', 'H'])

            for i in range(1, divisions):
                pillar_coord = (middle, math.floor(spacing * i))
                if not vertical:
                    pillar_coord = flipped(pillar_coord)
                removed_tiles = place_pillar(tile_map, offset(pillar_coord), pillar_shape, center_wide, vertical)
                all_tiles -= removed_tiles

    room_furnisher(world, chunk_properties, tile_map, all_tiles)

def place_pillar(tile_map, position, shape, is_wide, wide_on_x):
    cut_tiles = set()
    start_x, start_y = position

    def cut(x, y):
        cut_tiles.add((x, y))
        tile_map.clear_tile(x, y)

    def cut_minus():
        cut(start_x, start_y)
        if wide_on_x:
            cut(start_x - 1, start_y)
            cut(start_x + 1, start_y)
            if is_wide:
                cut(start_x + 2, start_y)
        else:
            cut(start_x, start_y - 1)
            cut(start_x, start_y + 1)
            if is_wide:
                cut(start_x, start_y + 2)

    def cut_plus():
        cut_minus()
        if wide_on_x:
            cut(start_x, start_y - 1)
            cut(start_x, start_y + 1)
            if is_wide:
                cut(start_x + 1, start_y - 1)
                cut(start_x + 1, start_y + 1)
        else:
            cut(start_x - 1, start_y)
            cut(start_x + 1, start_y)
            if is_wide:
                cut(start_x - 1, start_y + 1)
                cut(start_x + 1, start_y + 1)

    def cut_corners():
        cut(start_x - 1, start_y - 1)
        two = 2 if is_wide else 1
        if wide_on_x:
            cut(start_x + two, start_y - 1)
            cut(start_x + two, start_y + 1)
            cut(start_x - 1, start_y + 1)
        else:
            cut(start_x - 1, start_y + two)
            cut(start_x + 1, start_y + two)
            cut(start_x + 1, start_y - 1)

    def cut_square():
        cut_plus()
        cut_corners()

    def cut_h():
        cut_minus()
        cut_corners()

    if shape == '-':
        cut_minus()
    elif shape == '+':
        cut_plus()
    elif shape == 'square':
        cut_square()
    elif shape == 'H':
        cut_h()

    return cut_tiles


def outer_ring_furnisher(world, chunk_properties, tile_map, ring_start, ring_stop):
    all_tiles = set()

    for i in range(0, TM_CHUNK_SIZE - 1):
        for j in range(0, TM_CHUNK_SIZE - 1):
            if i >= ring_start and i <= ring_stop and j >= ring_start and j <= ring_stop:
                continue
            all_tiles.add((i, j))

    def cut(x, y):
        all_tiles.remove((x, y))
        tile_map.clear_tile(x, y)

    cut_corner_chance = 60
    if random.randint(1, 100) <= cut_corner_chance:
        cut(0, 0)
        cut(TM_CHUNK_SIZE - 2, 0)
        cut(0, TM_CHUNK_SIZE - 2)
        cut(TM_CHUNK_SIZE - 2, TM_CHUNK_SIZE - 2)

    room_furnisher(world, chunk_properties, tile_map, all_tiles)

def room_furnisher(world, chunk_properties, tile_map, all_tiles):
    area = len(all_tiles)
    chunk_pos = chunk_properties['position']

    if area <= 12:
        include_enemies = random.choice([0, 0, 0, 0, 0, 1, 1])
        include_pots = random.choice([0, 0, 1, 1, 2])
    elif area <= 35:
        include_enemies = random.choice([0, 0, 0, 0, 1, 1, 2])
        include_pots = random.choice([0, 0, 0, 1, 2])
    elif area <= 55:
        include_enemies = random.choice([0, 0, 0, 1, 1, 2, 3])
        include_pots = random.choice([0, 1, 1, 3, 6])
    else:
        include_enemies = random.choice([0, 0, 1, 2, 4, 5, 6])
        include_pots = random.choice([0, 2, 5, 7, 8])

    # dont pack the room full of stuff
    max_things = area // 3

    stuff_so_far = 0

    unused_spots = list(all_tiles)

    visible = GameSettings.debug_mode

    # Random chance that first pot in a room gets replaced with a chest
    do_chest = random.randint(1, 10) < 2

    for i in range(include_pots):
        spot = random.choice(unused_spots)
        unused_spots.remove(spot)
        spot_x, spot_y = spot

        subtype = 'pot'
        if i == 0 and do_chest:
            subtype = 'chest'

        world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, spot_x, spot_y)
        world.add_entity_at(world_x, world_y, visible, 'bustable', subtype)

        stuff_so_far += 1
        if stuff_so_far >= max_things:
            return

    enemy_sets = [
        ['goon'],
        ['peaceful_goon'],
        ['goon', 'goon', 'goon', 'cubeo'],
        ['cubeo', 'cubeo', 'big_cubeo'],
        ['mini_pod', 'cubeo', 'goon'],
        ['mini_pod'],
        ['eyepod'],
    ]
    enemy_set_weights = [6, 9, 6, 6, 4, 2, 1]
    enemy_set = random.choices(enemy_sets, weights=enemy_set_weights)[0]

    # Only spawn eyepod by himself
    if enemy_set == ['eyepod']:
        include_enemies = 1

    for i in range(include_enemies):
        spot = random.choice(unused_spots)
        unused_spots.remove(spot)
        spot_x, spot_y = spot

        enemy_type = random.choice(enemy_set)

        world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, spot_x, spot_y)
        world.add_entity_at(world_x, world_y, visible, 'creature', enemy_type)

        stuff_so_far += 1
        if stuff_so_far >= max_things:
            return

    floor_prefix = chunk_properties['color'] + '_'
    rare_variants = 0
    if chunk_properties['color'] == 'classic':
        rare_variants = 2
    if chunk_properties['color'] == 'rock':
        rare_variants = 1

    def rare_tile_img():
        if rare_variants < 2:
            return floor_prefix + 'floor3'
        return floor_prefix + 'floor' + str(random.randint(1, rare_variants) + 2)

    if rare_variants > 0:
        # 50% chance of a few rare variants
        # 25% chance of a lot of rare variants
        cracks_count = 0
        if random.randint(1, 2) == 2:
            cracks_count = area // 10
        elif random.randint(1, 2) == 2:
            cracks_count = area // 5

        for i in range(cracks_count):
            if len(unused_spots) < 1:
                break
            spot = random.choice(unused_spots)
            unused_spots.remove(spot)
            spot_x, spot_y = spot

            tile_map.clear_tile(spot_x, spot_y)
            tile_map.place_tile(spot_x, spot_y, visible, rare_tile_img())

# Place inter-chunk tiles and doors
# do it before chopping rooms so they can avoid chopping right next to the doors
def place_doors(world, tile_map, chunk_pos, chunk_properties, floor_data):
    chunk_x, chunk_y = chunk_pos
    visible = GameSettings.debug_mode

    floor_prefix = chunk_properties['color'] + '_'
    floor_variants = 2

    def floor_tile_img():
        return floor_prefix + 'floor' + str(random.randint(1, floor_variants))

    if (chunk_x, chunk_y, 'right') in floor_data['doors']:
        door_y = floor_data['doors'][(chunk_x, chunk_y, 'right')]
        door_x = TM_CHUNK_SIZE - 1
        tile_map.place_tile(door_x, door_y, visible, floor_tile_img())

        world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, door_x, door_y)
        door = world.add_entity_at(world_x, world_y, visible, 'door', 'door')
    if (chunk_x, chunk_y, 'down') in floor_data['doors']:
        door_x = floor_data['doors'][(chunk_x, chunk_y, 'down')]
        door_y = TM_CHUNK_SIZE - 1
        tile_map.place_tile(door_x, door_y, visible, floor_tile_img())

        world_x, world_y = world.chunk_coord_to_world_coord(chunk_pos, door_x, door_y)
        door = world.add_entity_at(world_x, world_y, visible, 'door', 'door')
