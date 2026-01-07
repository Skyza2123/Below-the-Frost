from settings import *
from os.path import join, basename
from os import walk
from pytmx.util_pygame import load_pygame

# imports 
def import_image(*path, alpha = True, format = 'png'):
	full_path = join(*path)
	# if the last path component already includes an extension, don't append the format
	if '.' not in basename(full_path) and format:
		full_path = full_path + f'.{format}'
	surf = pygame.image.load(full_path).convert_alpha() if alpha else pygame.image.load(full_path).convert()
	return surf

def import_folder(*path):
	frames = []
	for folder_path, sub_folders, image_names in walk(join(*path)):
		for image_name in sorted(image_names, key = lambda name: int(name.split('.')[0])):
			full_path = join(folder_path, image_name)
			surf = pygame.image.load(full_path).convert_alpha()
			frames.append(surf)
	return frames

def import_folder_dict(*path):
	frames = {}
	for folder_path, sub_folders, image_names in walk(join(*path)):
		for image_name in image_names:
			full_path = join(folder_path, image_name)
			surf = pygame.image.load(full_path).convert_alpha()
			frames[image_name.split('.')[0]] = surf
	return frames

def import_sub_folders(*path):
	frames = {}
	for _, sub_folders, __ in walk(join(*path)):
		if sub_folders:
			for sub_folder in sub_folders:
				frames[sub_folder] = import_folder(*path, sub_folder)
	return frames

def import_tilemap(cols, rows, *path):
	frames = {}
	surf = import_image(*path)
	cell_width, cell_height = surf.get_width() / cols, surf.get_height() / rows
	for col in range(cols):
		for row in range(rows):
			cutout_rect = pygame.Rect(col * cell_width, row * cell_height,cell_width,cell_height)
			cutout_surf = pygame.Surface((cell_width, cell_height))
			cutout_surf.fill('green')
			cutout_surf.set_colorkey('green')
			cutout_surf.blit(surf, (0,0), cutout_rect)
			frames[(col, row)] = cutout_surf
	return frames

ACTIONS = [
    ("idle",   4),
    ("walk",   6),
    ("run",    6),
    ("lift",   4),
    ("strike", 4),
    ("chop",   4),
    ("reap",   4),
]

# order as it appears on the sheet
SHEET_DIRS = ["forward", "backward", "left", "right"]

# map sheet naming -> engine naming
DIR_MAP = {"forward": "down", "backward": "up", "left": "left", "right": "right"}

def character_importer(cols, rows, *path):
    frame_dict = import_tilemap(cols, rows, *path)  # {(col,row): Surface}
    new_dict = {}

    idx = 0
    for action_name, frames_per_dir in ACTIONS:
        new_dict[action_name] = {}
        for sheet_dir in SHEET_DIRS:
            engine_dir = DIR_MAP[sheet_dir]
            frames = []
            for _ in range(frames_per_dir):
                r, c = divmod(idx, cols)
                frames.append(frame_dict[(c, r)])
                idx += 1
            new_dict[action_name][engine_dir] = frames

    return new_dict



def all_character_import(*path):
    new_dict = {}
    for _, __, image_names in walk(join(*path)):
        for image_name in image_names:
            if not image_name.lower().endswith((".png", ".webp", ".bmp", ".jpg", ".jpeg")):
                continue
            char_name = image_name.rsplit(".", 1)[0]
            # IMPORTANT: cols/rows must match your sheet grid (tiles), not 16x32 body size.
            # Example for many of your 48x48 sheets: 8 cols x 16 rows (adjust if different).
            new_dict[char_name] = character_importer(8, 16, *path, image_name)

    return new_dict

def coast_importer(cols, rows, *path):
	frame_dict = import_tilemap(cols, rows, *path)
	new_dict = {}
	terrains = ['grass', 'grass_i', 'sand_i', 'sand', 'rock', 'rock_i', 'ice', 'ice_i']
	sides = {'topleft': (0,0), 'top': (1,0), 'topright': (2,0), 
		  'left': (0,1), 'right': (2,1), 'bottomleft': (0,2), 
		  'bottom': (1,2), 'bottomright': (2,2)
		  }
	for index, terrain in enumerate(terrains):
		new_dict[terrain] = {}
		for key, pos in sides.items():
			new_dict[terrain][key] = frame_dict[(pos[0] + index * 3, pos[1])]

	return new_dict

def tmx_importer(*path):
	tmx_dict = {}

# game functions 

def check_connections(radius, entity, target, tolerance = 30):
	relation = vector(target.rect.center) - vector(entity.rect.center)
	if relation.length() < radius:
		if entity.facing_direction == 'left' and relation.x < 0 and abs(relation.y) < tolerance or \
		   entity.facing_direction == 'right' and relation.x > 0 and abs(relation.y) < tolerance or \
		   entity.facing_direction == 'up' and relation.y < 0 and abs(relation.x) < tolerance or \
		   entity.facing_direction == 'down' and relation.y > 0 and abs(relation.x) < tolerance:
			return True	