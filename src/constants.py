
GAME_SCALE = 1
TM_CHUNK_SIZE = 26

class GameSettings:
    game_scale = 1

    enable_fps = False

def get_screen_center_offset():
    return (-100 * GameSettings.game_scale, -75 * GameSettings.game_scale)
