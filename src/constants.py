
TM_CHUNK_SIZE = 26

GRID_WIDTH = 18

PATHFINDING_WIDTH = 70
PATHFINDING_HEIGHT = 70

PATHFINDING_CENTER_DEADZONE = 20

class GameSettings:
    game_scale = 1

    enable_fps = False

def get_screen_center_offset():
    return (-135 * GameSettings.game_scale, -100 * GameSettings.game_scale)
