from constants import *

import random
from tilemap import TileMap

def generate_floor():
    worms = 2
    chunks_per = 4
    chunks = set()

    directions [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for worm_i in range(worms):
        cur_x = 0
        cur_y = 0

        set_chunks = 0
        while set_chunks < chunks_per:
            chunk_pos = (cur_x, cur_y)
            if chunk_pos not in chunks:
                chunks.add(chunk_pos)
                set_chunks += 1

            xd, yd = random.choice(directions)
            cur_x += xd
            cur_y += yd

    # define inter-chunk door positions
    doors = {}
    for chunk_pos in chunks:
        this_chunk_x, this_chunk_y = chunk_pos

        if (this_chunk_x + 1, this_chunk_y) in chunks:
            doors[(this_chunk_x, this_chunk_y, 'right')] = random.randint(0, TM_CHUNK_SIZE - 2)

        if (this_chunk_x, this_chunk_y + 1) in chunks:
            doors[(this_chunk_x, this_chunk_y, 'down')] = random.randint(0, TM_CHUNK_SIZE - 2)

    return {'chunks': chunks, 'starting-chunk': random.choice(chunks), 'doors': doors}


def generate_chunk(world, floor_data, chunk_pos):
    chunk_x, chunk_y = chunk_pos
    chunk_map = TileMap()
    world.add_chunk(chunk_x, chunk_y, chunk_map)

    floor_variants = 2

    visible = GameSettings.enable_fps

    # Fill whole chunk first
    for x in range(TM_CHUNK_SIZE):
        for y in range(TM_CHUNK_SIZE):
            chunk_map.place_tile(x, y, visible, 'floor' + str(random.randint(1, floor_variants)))

    # Chop up vertically and horizontally to create irregular rooms
    recursive_room_chopper(world, chunk_map, chunk_pos, 0, 0, TM_CHUNK_SIZE, TM_CHUNK_SIZE, 1)

def recursive_room_chopper(world, tile_map, chunk_pos, x, y, w, h, depth):
    done = False
    # infinite recursion protection
    if depth > 25:
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
        room_furnisher(world, tile_map, x, y, w, h)
        return

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
        dc_positions = []
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
            stuff = world.what_is_at(door_check_x, door_check_y)
            if stuff['tile']:
                # theres some tile in the wall, I can assume theres a door there
                #print("Stopped an invalid cut")
                valid_cut = False
        # Door check done
        #######################

        cut_tries -= 1
        if cut_tries < 0:
            # couldn't get a valid cut in a few tries so we'll just not cut this room any further
            room_furnisher(world, tile_map, x, y, w, h)
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
                door = world.add_entity_at(vx, vy, False, 'door', 'door')
                door.closed = True
        else:
            tile_map.clear_tile(vx, vy)

    # Recurse
    if vertical:
        recursive_room_chopper(world, tile_map, chunk_pos, x, y, slice_position, h, depth + 1)
        recursive_room_chopper(world, tile_map, chunk_pos, x + slice_position + 1, y, w - 1 - slice_position, h, depth + 1)
    else:
        recursive_room_chopper(world, tile_map, chunk_pos, x, y, w, slice_position, depth + 1)
        recursive_room_chopper(world, tile_map, chunk_pos, x, y + slice_position + 1, w, h - 1 - slice_position, depth + 1)

def room_furnisher(world, tile_map, x, y, w, h):
    area = w * h

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

    unused_spots = []
    for i in range(x, x + w):
        for j in range(y, y + h):
            unused_spots.append((i, j))

    # Random chance that first pot in a room gets replaced with a chest
    do_chest = random.randint(1, 10) < 2

    for i in range(include_pots):
        spot = random.choice(unused_spots)
        unused_spots.remove(spot)
        spot_x, spot_y = spot

        subtype = 'pot'
        if i == 0 and do_chest:
            subtype = 'chest'
        world.add_entity_at(spot_x, spot_y, False, 'bustable', subtype)

        stuff_so_far += 1
        if stuff_so_far >= max_things:
            return

    enemy_sets = [
        ['goon'],
        ['goon', 'goon', 'goon', 'cubeo'],
        ['cubeo', 'cubeo', 'big_cubeo']
    ];
    # Random chance of eyepod in room with 1 enemy
    if include_enemies == 1 and random.randint(1, 9) < 2:
        enemy_sets = [['eyepod']]
    enemy_set = random.choice(enemy_sets)
    for i in range(include_enemies):
        spot = random.choice(unused_spots)
        unused_spots.remove(spot)
        spot_x, spot_y = spot

        enemy_type = random.choice(enemy_set)
        world.add_entity_at(spot_x, spot_y, False, 'creature', enemy_type)

        stuff_so_far += 1
        if stuff_so_far >= max_things:
            return

    # 50% chance of slightly cracked floor
    # 25% chance of very cracked floor
    cracks_count = 0
    if random.randint(1, 2) == 2:
        cracks_count = area // 10
    elif random.randint(1, 2) == 2:
        cracks_count = area // 5

    crack_variants = 2
    for i in range(cracks_count):
        if len(unused_spots) < 1:
            break
        spot = random.choice(unused_spots)
        unused_spots.remove(spot)
        spot_x, spot_y = spot

        tile_map.clear_tile(spot_x, spot_y)
        tile_map.place_tile(spot_x, spot_y, False, 'floor_crack' + str(random.randint(1, crack_variants)))

