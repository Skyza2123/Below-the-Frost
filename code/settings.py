import pygame
from pygame.math import Vector2 as vector 
from sys import exit

WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
TILE_SIZE = 64 
ANIMATION_SPEED = 4
BATTLE_OUTLINE_WIDTH = 4

# Gamepad mappings (common Xbox-style layout). Adjust if your controller differs.
GAMEPAD_INDEX = 0
GAMEPAD_DEADZONE = 0.2
GP_A = 0
GP_B = 1
GP_X = 2
GP_Y = 3
GP_LB = 9
GP_RB = 10
GP_BACK = 6
GP_START = 4
GP_LS = 8
GP_RS = 11
GP_HAT = 0
# Some controllers report the D-PAD as buttons instead of a hat. Map those here.
DPAD_BUTTON_UP = 11
DPAD_BUTTON_DOWN = 12
DPAD_BUTTON_LEFT = 13
DPAD_BUTTON_RIGHT = 14
# allow an additional run button (e.g. RB/RS press or other); button index 9 is common
GP_RUN_BUTTON = 9

COLORS = {
	'white': '#f4fefa', 
	'pure white': '#ffffff',
	'dark': '#2b292c',
	'light': '#c8c8c8',
	'gray': '#3a373b',
	'gold': '#ffd700',
	'light-gray': '#4b484d',
	'fire':'#f8a060',
	'water':'#50b0d8',
	'plant': '#64a990', 
	'black': '#000000', 
	'red': '#f03131',
	'blue': '#66d7ee'
}

WORLD_LAYERS = {
	'water': 0,
	'bg': 1,
	'shadow': 2,
	'main': 3,
	'top': 4
}

BATTLE_POSITIONS = {
	'left': {'top': (360, 260), 'center': (190, 400), 'bottom': (410, 520)},
	'right': {'top': (900, 260), 'center': (1110, 390), 'bottom': (900, 550)}
}

BATTLE_LAYERS =  {
	'outline': 0,
	'name': 1,
	'monster': 2,
	'effects': 3,
	'overlay': 4
}

BATTLE_CHOICES = {
	'full': {
		'fight':  {'pos' : vector(30, -60), 'icon': 'sword'},
		'defend': {'pos' : vector(40, -20), 'icon': 'shield'},
		'switch': {'pos' : vector(40, 20), 'icon': 'arrows'},
		'catch':  {'pos' : vector(30, 60), 'icon': 'hand'}},
	
	'limited': {
		'fight':  {'pos' : vector(30, -40), 'icon': 'sword'},
		'defend': {'pos' : vector(40, 0), 'icon': 'shield'},
		'switch': {'pos' : vector(30, 40), 'icon': 'arrows'}}
}

# Grid overlay for layout/debugging (pixels)
GRID_SIZE = 48
GRID_COLOR = (255, 255, 255)
GRID_ALPHA = 60  # 0-255

# Cutscene testing: set to True to auto-run the `CUTSCENE_AUTOSTART_ID` at map load
# for development. Leave False for production.
CUTSCENE_AUTOSTART = True