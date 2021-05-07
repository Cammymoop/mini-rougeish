
TM_CHUNK_SIZE = 26

GRID_WIDTH = 18

PATHFINDING_WIDTH = 80
PATHFINDING_HEIGHT = 80

PATHFINDING_CENTER_DEADZONE = 20


class GameSettings:
    game_scale = 1

    enable_fps = False
    debug_mode = False

    internal_w = 270
    internal_h = 200

    scaler = 3

def get_internal_res():
    return (GameSettings.internal_w * GameSettings.game_scale, GameSettings.internal_h * GameSettings.game_scale)

def get_real_res():
    return (GameSettings.internal_w * GameSettings.scaler, GameSettings.internal_h * GameSettings.scaler)

def get_screen_center_offset():
    return (-135 * GameSettings.game_scale, -100 * GameSettings.game_scale)
