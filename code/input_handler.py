import pygame
import math
from settings import *
from support import check_connections


def process_events(game, events):
    """Process Pygame events for the given Game instance.
    This mirrors the previous inlined logic but lives in a separate module.
    """
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit

        # handle grid clicks before UI so clicks on the overlay register
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(game, 'show_grid', False):
            sx, sy = event.pos
            off = game.all_sprites.offset
            # world coordinates = screen - offset
            wx = sx - off.x
            wy = sy - off.y

            # grid cell indices
            gx = int(math.floor(wx / game.grid_size))
            gy = int(math.floor(wy / game.grid_size))

            cell_world_x = gx * game.grid_size
            cell_world_y = gy * game.grid_size
            cell_screen_x = cell_world_x + off.x
            cell_screen_y = cell_world_y + off.y

            now = pygame.time.get_ticks()
            game.grid_clicks.append({
                'screen': (sx, sy),
                'world': (int(wx), int(wy)),
                'grid': (gx, gy),
                'cell_screen': (int(cell_screen_x), int(cell_screen_y)),
                'expiry': now + 3000
            })
            # consume event so UI doesn't also act on this click
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            game.show_hitboxes = not game.show_hitboxes
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
            game.show_grid = not game.show_grid
        # adjust grid size with +/- keys when grid is visible
        if event.type == pygame.KEYDOWN and game.show_grid:
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                game.grid_size = min(256, game.grid_size + 4)
            elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                game.grid_size = max(4, game.grid_size - 4)

        # UI FIRST (pause + tab)
        if game.ui_manager.handle_event(event):
            continue

        # Controller: A opens dialog when near NPC (ONLY if no UI modal open)
        if event.type == pygame.JOYBUTTONDOWN and not game.ui_manager.modal_open:
            if event.button == GP_A:
                if not game.dialog_tree:
                    for character in game.character_sprites:
                        if check_connections(80, game.player, character):
                            game.player.block()
                            character.change_facing_direction(game.player.rect.center)
                            game.create_dialog(character)
                            break
                else:
                    if hasattr(game.dialog_tree, "advance"):
                        game.dialog_tree.advance()

        if event.type == pygame.JOYAXISMOTION:
            # apply deadzone and debounce per (joy, axis)
            raw = float(event.value)
            key = (event.joy, event.axis)
            val = 0.0 if abs(raw) < game.axis_deadzone else raw
            last = game._axis_prev.get(key, 0.0)
            # print only significant changes to reduce spam
            if abs(val - last) > 0.15:
                print(f"JOYAXISMOTION: joy={event.joy} axis={event.axis} value={raw:.3f} -> clamped={val:.3f}")
                game._axis_prev[key] = val

