import logging
import os
from PIL import Image

IMAGE_SIZE = (792, 600)
THUMBNAIL_WIDTH = 132
THUMBNAIL_HEIGHT = 100
TILE_SIZE = 24
BORDER_SIZE = 2
COPY_SIZE = TILE_SIZE + 2 * BORDER_SIZE
SOURCE_IMG = os.path.join(os.path.dirname(__file__), 'composite.png')
BACKGROUND_COLOR = (202, 202, 202)
FOREGROUND_COLOR = (121, 121, 136)

_sprites = Image.open(SOURCE_IMG)

tiles = '3245GFHI?>@A7689QPNOKJLMCBDE;:<=10'
tilemap = dict(zip(tiles, range(len(tiles))))


def _object_with_coordinates(sprite_id, x_offset=12, y_offset=12, extra_args=0):
    def obj_fun(x, y, *args):
        if x == 'NaN' or y == 'NaN': return []
        if len(args) != extra_args:
            raise TypeError("obj_fun takes exactly %d arguments (%d given)", extra_args + 2, len(args) + 2)
        return [(int(float(x)) - x_offset, int(float(y)) - y_offset, sprite_id)]
    return obj_fun

launchpad_sprites = {
    (-1, -1): 68,
    (0, -1): 67,
    (1, -1): 66,
    (-1, 0): 61,
    (1, 0): 65,
    (-1, 1): 62,
    (0, 1): 63,
    (1, 1): 64,
}

def _launchpad(x, y, ygrad, xgrad):
    x, y, xgrad, ygrad = int(x), int(y), float(xgrad), float(ygrad)
    quadrant = (cmp(xgrad, 0), cmp(ygrad, 0))
    return [(x - 12, y - 12, launchpad_sprites[quadrant])]

def _drone(x, y, _, has_pathfinding, drone_type, direction):
    x, y = int(float(x)), int(float(y))
    if direction == 'NaN':
        direction = 1
    else:
        direction = int(direction)
    drone_type, has_pathfinding = int(drone_type), int(has_pathfinding)

    sprite_id = 42
    if drone_type == 1:
        sprite_id += 8
    elif drone_type == 2:
        sprite_id += 12
    sprite_id += has_pathfinding * 4
    sprite_id += direction
    return [(x - 12, y - 12, sprite_id)]

def _object_with_direction(sprite_id):
    def obj_dir_fun(x, y, dir):
        if x == 'NaN' or y == 'NaN':
            return []
        if dir == 'NaN':
            dir = 0
        else:
            dir = int(dir)
        return [(int(float(x)) - 12, int(float(y)) - 12, sprite_id + dir)]
    return obj_dir_fun

door_sprites = {
    (0, 0, 0, -1): 79,
    (0, 0, 0, 0): 77,
    (0, 0, 1, -1): 80,
    (0, 0, 1, 0): 78,
    (0, 1, 0, -1): 33,
    (0, 1, 0, 0): 33,
    (0, 1, 1, -1): 33,
    (0, 1, 1, 0): 33,
    (1, 0, 0, -1): 83,
    (1, 0, 0, 0): 81,
    (1, 0, 1, -1): 84,
    (1, 0, 1, 0): 82,
}

def _door(panel_x, panel_y, is_vertical, is_trapdoor, tile_x, tile_y, locked, xdir, ydir):
    if xdir == 'NaN' or ydir == 'NaN':
        dir = 0
    else:
        dir = int(xdir) + int(ydir)
    sprite_id = door_sprites.get((int(locked), int(is_trapdoor), int(is_vertical), dir))
    if not sprite_id: return []

    if locked == '0':
        if is_trapdoor == '0':
            panel_sprite = 33
        else:
            panel_sprite = 86
    else:
        panel_sprite = 85
    return [
        (TILE_SIZE * int(tile_x), TILE_SIZE * int(tile_y), sprite_id),
        (int(panel_x) - 12, int(panel_y) - 12, panel_sprite)
    ]

def _exit(door_x, door_y, panel_x, panel_y):
    door_x, door_y, panel_x, panel_y = int(door_x), int(door_y), int(panel_x), int(panel_y)
    return [
        (door_x - 12, door_y - 12, 75),
        (panel_x - 12, panel_y - 12, 76),
    ]

objectmap = {
    '0': _object_with_coordinates(59), # Gold
    '1': _object_with_coordinates(60), # Bounce block
    '2': _launchpad,
    '3': _object_with_coordinates(34), # Gauss turret
    '4': _object_with_coordinates(37, y_offset=18, extra_args=1), # Floor guard
    '5': _object_with_coordinates(58), # N
    '6': _drone, # Drone
    '7': _object_with_direction(71), # One way platform
    '8': _object_with_direction(38), # Thwump
    '9': _door, # Door
    '10': _object_with_coordinates(35), # Rocket turret
    '11': _exit, # Exit
    '12': _object_with_coordinates(36), # Mine
}

class InvalidLevelError(Exception): pass

def parse_level(leveldata):
    leveldata = leveldata.split('|')
    if len(leveldata) < 2:
        raise InvalidLevelError("Level must have both terrain and objects.")
    terrain, objects = leveldata[:2]
    
    if len(terrain) != 713:
        raise InvalidLevelError("Expected 713 characters of tile data, got %d" % (len(terrain),))
    terrain = [tilemap.get(x, 33) for x in terrain]
    
    object_list = []
    for obj in objects.split('!'):
        object_id, object_data = obj.split('^')[:2]
        if not object_id or not object_data:
            # Can't parse object; skip it
            logging.error("Missing objectid or object data")
            continue
        object_data = object_data.split(',')
        draw_func = objectmap.get(object_id)
        try:
            object_list.extend(draw_func(*object_data))
        except Exception, ex:
            logging.exception("Handling object with id %s and data %r" % (object_id, object_data))

    return terrain, object_list


def generate_level_image(terrain, object_list):
    level_image = Image.new("RGB", IMAGE_SIZE, BACKGROUND_COLOR)
    
    draw_objects(level_image, object_list)
    
    # Draw the border
    level_image.paste(FOREGROUND_COLOR, (0, 0, IMAGE_SIZE[0] - 1, TILE_SIZE))
    level_image.paste(FOREGROUND_COLOR, (0, 0, TILE_SIZE, IMAGE_SIZE[1] - 1))
    level_image.paste(FOREGROUND_COLOR, (0, IMAGE_SIZE[1] - TILE_SIZE - 1, IMAGE_SIZE[0] - 1, IMAGE_SIZE[1] - 1))
    level_image.paste(FOREGROUND_COLOR, (IMAGE_SIZE[0] - TILE_SIZE - 1, 0, IMAGE_SIZE[0] - 1, IMAGE_SIZE[1] - 1))
    
    draw_tiles(level_image, terrain)
    return level_image


def draw_objects(level_image, object_list):
    for x, y, sprite_id in object_list:
        sprite = _sprites.crop((sprite_id * COPY_SIZE, 0, (sprite_id + 1) * COPY_SIZE, COPY_SIZE))
        level_image.paste(sprite, (x - BORDER_SIZE, y - BORDER_SIZE), sprite)


def draw_tiles(level_image, terrain):
    tile_sprites = iter(terrain)
    for x in range(TILE_SIZE, IMAGE_SIZE[0] - TILE_SIZE, TILE_SIZE):
        for y in range(TILE_SIZE, IMAGE_SIZE[1] - TILE_SIZE, TILE_SIZE):
            sprite_id = tile_sprites.next()
            sprite = _sprites.crop((sprite_id * COPY_SIZE, 0, (sprite_id + 1) * COPY_SIZE, COPY_SIZE))
            level_image.paste(sprite, (x - BORDER_SIZE, y - BORDER_SIZE), sprite)
