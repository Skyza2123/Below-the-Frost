# main.py
from settings import *
from pytmx.util_pygame import load_pygame
from os.path import join
from game_data import *

from sprites import Sprite, AnimatedSprite, MonsterPatchSprite, BorderSprite, CollideableSprite, TransitionSprite
from entites import Player, Character
from groups import AllSprites

from support import *
from dialog import DialogTree
from ui_helper import *

# ✅ NEW IMPORTS (match your folder layout)
from ui.ui_manager import UIManager
from ui.ui_assets import UIAssets
from ui.overlays.pause_menu import PauseMenu
from ui.overlays.tab_menu import TabMenu
from dialog_renderer import draw_dialog
import sys
import os
import math
from input_handler import process_events
from frame_renderer import frame_step

# ensure project root is on sys.path so imports like `data_characters` work
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from data_characters import CHARACTERS
from cutscenes.registry import get_cutscene
from cutscenes.runner import CutSceneManager



class Game:
    def __init__(self):
        pygame.init()

        # initialize joystick subsystem and attach controllers
        pygame.joystick.init()
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()  
            self.joysticks.append(joy)

        # input logging helpers
        self.axis_deadzone = 0.2
        # store last meaningful axis values to avoid spamming logs
        self._axis_prev: dict[tuple[int, int], float] = {}
        self._button_prev: dict[tuple[int, int], bool] = {}

        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Below the Frost")
        self.clock = pygame.time.Clock()

        # transition sprites
        self.transition_target = None
        self.tint_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.tint_mode = 'idle'
        self.tint_progress = 0
        self.tint_direction = 1
        self.tint_speed = 300  # alpha units per second
        # prevent immediate re-triggering of transition zones after teleport
        self.transition_cooldown = 0.0
        self.transition_cooldown_time = 0.5

        # groups
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.character_sprites = pygame.sprite.Group()
        self.transition_sprites = pygame.sprite.Group()

        self.import_assets()
        self.setup(self.tmx_maps["world"], "house")

        self.dialog_tree = None
        self.show_hitboxes = False
        self.show_grid = False
        # runtime grid size (pixels) and small font for overlay
        self.grid_size = GRID_SIZE
        self.grid_font = pygame.font.Font(join("graphics", "fonts", "PixeloidSans.ttf"), 16)
        # stored click markers when grid is active
        self.grid_clicks: list[dict] = []

        # ------------------------------------------------------------
        # UI ASSETS (ONE PLACE)
        # ------------------------------------------------------------
        # Your UIAssets should load + scale surfaces/fonts once:
        # - dialog panel
        # - menu panels
        # - tab frames/icons
        # - dim overlay, etc.
        self.ui_assets = UIAssets(
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            base_path="graphics",
        )

        # ------------------------------------------------------------
        # OVERLAYS
        # ------------------------------------------------------------
        self.pause_menu = PauseMenu(
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            assets=self.ui_assets,   # <-- reuse ui assets
            btn_confirm=GP_A,
            btn_back=GP_B,
            btn_start=GP_START,
        )

        # Choose your toggle for the tab/journal menu:
        # Keyboard: TAB
        # Controller: usually SELECT / BACK
        self.tab_menu = TabMenu(
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            assets=self.ui_assets,
            btn_confirm=GP_A,
            btn_back=GP_B,
            btn_toggle=GP_BACK,  # ✅ Back button toggles journal
            title_provider=lambda: CHARACTERS.get(getattr(self.player, "character_id", "raya"), {}).get("name", "Player"),
            character_id_provider=lambda: getattr(self.player, "character_id", "raya"),
        )



        

        # UI manager routes input/draw order (top overlay gets input first)
        self.ui_manager = UIManager([self.tab_menu, self.pause_menu])

        # Cutscene manager
        self.cutscene_manager = CutSceneManager(self.display_surface)
        # map -> entry cutscene id (played after fade-in when entering a map)
        self.entry_cutscenes = {
            "hospital": "test_raya_enters_hospital",
        }
        self.current_map_key = None
        self._entry_cutscene_playing = False

        # pause menu actions
        def _pause_action(action: str):
            if action == "quit_desktop":
                pygame.quit()
                raise SystemExit
            if action == "open_settings":
                print("TODO: Settings submenu")

        self.pause_menu.on_action = _pause_action

        # OPTIONAL: tab menu action hook
        self.tab_menu.on_action = lambda action: None

    def import_assets(self):
        self.tmx_maps = {
            "world": load_pygame(join("data", "maps", "world.tmx")),
            "hospital": load_pygame(join("data", "maps", "hospital.tmx")),
        }

        self.overworld_frames = {
            "water": import_folder("graphics", "tilesets", "water"),
            "coast": coast_importer(24, 12, "graphics", "tilesets", "coast"),
            "characters": all_character_import("graphics", "characters"),
        }

        # You can keep this, but ideally your UIAssets owns UI fonts too
        self.font = {
            "dialog": pygame.font.Font(join("graphics", "fonts", "PixeloidSans.ttf"), 30)
        }

    def setup(self, tmx_map, player_start_pos):
        for group in (self.all_sprites, self.collision_sprites, self.character_sprites, self.transition_sprites):
            group.empty()
            
        # terrain setup
        for layer in ["Terrain", "Terrain Top"]:
            for x, y, surf in tmx_map.get_layer_by_name(layer).tiles():
                Sprite((x * TILE_SIZE, y * TILE_SIZE), surf, self.all_sprites, WORLD_LAYERS["bg"])

        # water setup
        for obj in tmx_map.get_layer_by_name("Water"):
            for x in range(int(obj.x), int(obj.x + obj.width), TILE_SIZE):
                for y in range(int(obj.y), int(obj.y + obj.height), TILE_SIZE):
                    AnimatedSprite((x, y), self.overworld_frames["water"], self.all_sprites, WORLD_LAYERS["water"])

        # coast setup
        for obj in tmx_map.get_layer_by_name("Coast"):
            terrain = obj.properties.get("terrain")
            side = obj.properties.get("side")
            AnimatedSprite(
                (obj.x, obj.y),
                [self.overworld_frames["coast"][terrain][side]],
                self.all_sprites,
                WORLD_LAYERS["bg"],
            )

        # object setup
        for obj in tmx_map.get_layer_by_name("Objects"):
            if obj.name == "top":
                Sprite((obj.x, obj.y), obj.image, self.all_sprites, WORLD_LAYERS["top"])
            else:
                CollideableSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))

        # transition setup
        for obj in tmx_map.get_layer_by_name("Transition"):
            # TransitionSprite signature: (pos, size, target, groups)
            # parse target and optional start pos from object properties
            target_prop = obj.properties.get("target")
            pos_prop = obj.properties.get("pos")
            TransitionSprite((obj.x, obj.y), (obj.width, obj.height), (target_prop, pos_prop), self.transition_sprites)

            
        # collision objects
        for obj in tmx_map.get_layer_by_name("Collisions"):
            BorderSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)

        # grass patches
        for obj in tmx_map.get_layer_by_name("Monsters"):
            MonsterPatchSprite((obj.x, obj.y), obj.image, self.all_sprites, obj.properties.get("biome"))
        # entity setup
        entities_layer = tmx_map.get_layer_by_name("Entities")

        # --- pick a Player spawn marker ---
        spawn_obj = None
        for obj in entities_layer:
            if obj.name != "Player":
                continue
            marker = obj.properties.get("pos")
            if isinstance(player_start_pos, str) and marker == player_start_pos:
                spawn_obj = obj
                break
            if spawn_obj is None:
                spawn_obj = obj  # fallback: first Player marker

        if spawn_obj is None:
            raise ValueError("TMX map is missing a Player object in the 'Entities' layer.")

        # --- create player (keep prior character if possible) ---
        prev_char_id = getattr(getattr(self, "player", None), "character_id", "raya")
        char_id = spawn_obj.properties.get("character_id", prev_char_id)
        frames = self.overworld_frames["characters"].get(char_id, self.overworld_frames["characters"]["raya"])

        self.player = Player(
            pos=(spawn_obj.x, spawn_obj.y),
            frames=frames,
            groups=(self.all_sprites, self.collision_sprites),
            facing_direction=spawn_obj.properties.get("direction"),
            collision_sprites=self.collision_sprites,
        )
        self.player.character_id = char_id

        # If the caller passed explicit coordinates, override the marker spawn position.
        if isinstance(player_start_pos, (list, tuple)) and len(player_start_pos) == 2:
            try:
                sx, sy = player_start_pos
                self.player.hitbox.center = (int(sx), int(sy))
                self.player.pos = vector(self.player.hitbox.center)
                if hasattr(self.player, "sync_rect_from_hitbox"):
                    self.player.sync_rect_from_hitbox()
                else:
                    self.player.rect.center = self.player.hitbox.center
            except Exception:
                pass

        # --- spawn NPCs ---
        for obj in entities_layer:
            if obj.name == "Player":
                continue
            Character(
                pos=(obj.x, obj.y),
                frames=self.overworld_frames["characters"].get(
                    obj.properties.get("graphic"),
                    self.overworld_frames["characters"]["raya"]
                ),
                groups=(self.all_sprites, self.collision_sprites, self.character_sprites),
                facing_direction=obj.properties.get("direction"),
                character_data=TRAINER_DATA.get(obj.properties.get("character_id")),
                character_id=obj.properties.get("character_id"),
            )

        # update cutscene context now that `player` and characters exist
        try:
            self.cutscene_manager.set_context({
                "game": self,
                "player": self.player,
                "character_sprites": self.character_sprites,
            })
        except Exception:
            pass

        # Auto-start a sample cutscene when entering the hospital map (for testing)
        try:
            if tmx_map is self.tmx_maps.get("hospital"):
                # When auto-starting the entrance cutscene, don't force-reset the
                # player's position if the script contains an initial `set_pos`.
                # Copy the cutscene data and remove a leading `set_pos` so the
                # cutscene begins from the player's current location.
                cs = get_cutscene("opening_raya_demo")
                script = cs.get("script", [])
                if script and script[0].get("type") == "set_pos":
                    import copy
                    cs_copy = copy.deepcopy(cs)
                    cs_copy["script"] = [c for i, c in enumerate(script) if not (i == 0 and c.get("type") == "set_pos")]
                    self.cutscene_manager.start_cutscene(cs_copy)
                else:
                    self.cutscene_manager.start_cutscene(cs)
        except Exception:
            pass

    # dialog functions
    def input(self):
        """World input (only when NO modal overlay is open)."""
        if self.dialog_tree:
            return

        keys = pygame.key.get_just_pressed()
        if keys[pygame.K_SPACE]:
            for character in self.character_sprites:
                if check_connections(80, self.player, character):
                    self.player.block()
                    character.change_facing_direction(self.player.rect.center)
                    self.create_dialog(character)
                    break

    def create_dialog(self, character):
        if not self.dialog_tree:
            self.dialog_tree = DialogTree(character, self.player, self.all_sprites, self.font["dialog"], self.end_dialog)

    def end_dialog(self, character):
        self.dialog_tree = None
        self.player.unblock()

    def _joy0(self):
        return self.joysticks[0] if self.joysticks else None
    
    # transition to new map
    def transition_check(self):
        # only trigger when we're not already mid-fade
        if self.tint_mode != 'idle' or self.transition_target is not None:
            return

        # skip triggering while cooldown active
        if getattr(self, 'transition_cooldown', 0.0) > 0:
            return

        # clear disabled flags ONLY once the player has actually left the zone
        for ts in self.transition_sprites:
            if getattr(ts, 'disabled', False) and not ts.rect.colliderect(self.player.hitbox):
                try:
                    ts.disabled = False
                    if hasattr(ts, 'disabled_until'):
                        delattr(ts, 'disabled_until')
                except Exception:
                    pass

        # find the first active transition sprite we're overlapping
        for sprite in self.transition_sprites:
            if getattr(sprite, 'disabled', False):
                continue
            if sprite.rect.colliderect(self.player.hitbox):
                self.player.block()
                self.transition_target = sprite.target
                self.tint_mode = 'tint'
                self.tint_progress = 0
                # NOTE: cooldown counts down only when idle (see tint_screen)
                self.transition_cooldown = self.transition_cooldown_time
                break

    def tint_screen(self, dt):
        # ------------------------------------------------------------
        # Fade state machine:
        #   idle    -> normal gameplay
        #   tint    -> fade to black (then load)
        #   untint  -> fade back in
        # ------------------------------------------------------------

        if self.tint_mode == 'tint':
            self.tint_progress = min(255, self.tint_progress + self.tint_speed * dt)

            if self.tint_progress >= 255:
                # lock at full black
                self.tint_progress = 255

                # perform map load using transition target (map_key, start_pos)
                tt = self.transition_target
                new_map_key = None
                new_start = None
                if isinstance(tt, (list, tuple)) and len(tt) >= 1:
                    new_map_key = tt[0]
                    new_start = tt[1] if len(tt) > 1 else None

                new_map = self.tmx_maps.get(new_map_key) if new_map_key else None
                if new_map is not None:
                    try:
                        # remember the map key we loaded for entry cutscene lookup
                        self.current_map_key = new_map_key
                        self.setup(new_map, new_start)
                    except Exception:
                        # don't crash the game if a transition target is misconfigured
                        pass

                # keep player blocked during the fade-in so you don't immediately retrigger zones
                try:
                    self.player.block()
                except Exception:
                    pass

                # disable any transition zone the player is currently inside (prevents "bounce back")
                try:
                    now = pygame.time.get_ticks()
                    for ts in self.transition_sprites:
                        if ts.rect.colliderect(self.player.hitbox):
                            ts.disabled = True
                            ts.disabled_until = now + int(self.transition_cooldown_time * 1000)
                except Exception:
                    pass

                # reset transition target and begin fade back in
                try:
                    self.transition_target = None
                    self.tint_mode = 'untint'
                except Exception:
                    self.transition_target = None
                    self.tint_mode = 'untint'

        elif self.tint_mode == 'untint':
            self.tint_progress = max(0, self.tint_progress - self.tint_speed * dt)

            if self.tint_progress <= 0:
                # back to gameplay
                self.tint_progress = 0
                # fade complete; normally return to idle, but if this map
                # has a configured entry cutscene, start it now and keep the
                # player blocked until it finishes.
                self.tint_mode = 'idle'
                try:
                    entry_id = self.entry_cutscenes.get(self.current_map_key)
                except Exception:
                    entry_id = None

                if entry_id:
                    try:
                        # skip if already completed
                        if getattr(self.cutscene_manager, 'completed', None) and entry_id in self.cutscene_manager.completed:
                            entry_id = None
                    except Exception:
                        pass

                if entry_id:
                    try:
                        cs = get_cutscene(entry_id)
                        self.cutscene_manager.set_context({
                            'game': self,
                            'player': self.player,
                            'character_sprites': self.character_sprites,
                        })
                        started = self.cutscene_manager.start_cutscene(cs)
                        if started:
                            try:
                                self.player.block()
                            except Exception:
                                pass
                            self._entry_cutscene_playing = True
                            # leave tint_mode as 'idle' while cutscene runs
                    except Exception:
                        # fallback: restore control
                        try:
                            self.player.unblock()
                            self.player.controlled = True
                        except Exception:
                            pass
                else:
                    try:
                        self.player.unblock()
                        self.player.controlled = True
                    except Exception:
                        pass

        elif self.tint_mode == 'hold_cutscene':
            # Keep black until cutscene finishes; once finished, begin fade back in
            try:
                if not (getattr(self, 'cutscene_manager', None) and self.cutscene_manager.is_running()):
                    self.tint_mode = 'untint'
            except Exception:
                self.tint_mode = 'untint'

        # draw tint if there's visible alpha
        alpha = int(max(0, min(255, self.tint_progress)))
        if alpha > 0:
            try:
                self.tint_surface.fill((0, 0, 0))
                self.tint_surface.set_alpha(alpha)
                self.display_surface.blit(self.tint_surface, (0, 0))
            except Exception:
                pass

        # cooldown ONLY counts down when we're idle
        if self.tint_mode == 'idle' and getattr(self, 'transition_cooldown', 0.0) > 0:
            self.transition_cooldown = max(0.0, self.transition_cooldown - dt)


    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            self.display_surface.fill("black")

            # event loop
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit

                # Cutscene input (skip / advance subtitles) should take priority
                # over UI and gameplay input.
                if getattr(self, 'cutscene_manager', None) and self.cutscene_manager.is_running():
                    try:
                        if self.cutscene_manager.handle_event(event):
                            continue
                    except Exception:
                        pass
                
            
                # handle grid clicks before UI so clicks on the overlay register
                if event.type == pygame.MOUSEBUTTONDOWN and getattr(self, 'show_grid', False):
                    sx, sy = event.pos
                    off = self.all_sprites.offset
                    # world coordinates = screen - offset
                    wx = sx - off.x
                    wy = sy - off.y

                    # grid cell indices
                    gx = int(math.floor(wx / self.grid_size))
                    gy = int(math.floor(wy / self.grid_size))

                    cell_world_x = gx * self.grid_size
                    cell_world_y = gy * self.grid_size
                    cell_screen_x = cell_world_x + off.x
                    cell_screen_y = cell_world_y + off.y

                    now = pygame.time.get_ticks()
                    self.grid_clicks.append({
                        'screen': (sx, sy),
                        'world': (int(wx), int(wy)),
                        'grid': (gx, gy),
                        'cell_screen': (int(cell_screen_x), int(cell_screen_y)),
                        'expiry': now + 3000
                    })
                    # consume event so UI doesn't also act on this click
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                    self.show_hitboxes = not self.show_hitboxes
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                    self.show_grid = not self.show_grid
                # adjust grid size with +/- keys when grid is visible
                if event.type == pygame.KEYDOWN and self.show_grid:
                    if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        self.grid_size = min(256, self.grid_size + 4)
                    elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                        self.grid_size = max(4, self.grid_size - 4)

                # ✅ UI FIRST (pause + tab)
                if self.ui_manager.handle_event(event):
                    continue

                # Controller: A opens dialog when near NPC (ONLY if no UI modal open)
                if event.type == pygame.JOYBUTTONDOWN and not self.ui_manager.modal_open:
                    if event.button == GP_A:
                        if not self.dialog_tree:
                            for character in self.character_sprites:
                                if check_connections(80, self.player, character):
                                    self.player.block()
                                    character.change_facing_direction(self.player.rect.center)
                                    self.create_dialog(character)
                                    break
                        else:
                            if hasattr(self.dialog_tree, "advance"):
                                self.dialog_tree.advance()

            # UPDATE UI overlays every frame
            self.ui_manager.update(dt, joystick=self._joy0())

            # Render and update frame (world update, drawing, overlays, grid, transition, display)
            frame_step(self, dt)

class Cutscenes:
    pass

if __name__ == "__main__":
    game = Game()
    game.run()
