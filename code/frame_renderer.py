import pygame
import math
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, GRID_COLOR, GRID_ALPHA, COLORS
from dialog_renderer import draw_dialog


def frame_step(game, dt):
    # UPDATE world
    # If a cutscene is running, we update it *before* sprites so it can set the
    # player's direction/speed for this frame (movement + animation stay in sync).
    if not game.ui_manager.modal_open:
        cutscene_running = bool(getattr(game, 'cutscene_manager', None) and game.cutscene_manager.is_running())

        if cutscene_running:
            game.cutscene_manager.update(dt)

        # always update sprites so animations keep ticking
        game.all_sprites.update(dt)

        # normal gameplay input/dialog only when no cutscene is active
        if not cutscene_running:
            game.input()
            if game.dialog_tree:
                game.dialog_tree.update()

    # DRAW world
    game.display_surface.fill("black")
    game.all_sprites.draw(game.player.rect.center)

    # DRAW dialog
    draw_dialog(game, game.display_surface)

    # allow active cutscenes to draw overlays (on top of world, before UI)
    if getattr(game, 'cutscene_manager', None):
        try:
            game.cutscene_manager.draw()
        except Exception:
            pass

    # DEBUG HITBOXES
    if getattr(game, 'show_hitboxes', False):
        off = game.all_sprites.offset
        pygame.draw.rect(game.display_surface, (255, 0, 0), game.player.hitbox.move(off.x, off.y), 2)
        for s in game.player.collision_sprites:
            hb = getattr(s, "hitbox", s.rect)
            pygame.draw.rect(game.display_surface, (0, 255, 0), hb.move(off.x, off.y), 1)

    # DRAW overlays on top
    game.ui_manager.draw(game.display_surface)

    # optional: world-aligned grid overlay for layout/debugging (drawn last to appear above UI)
    if getattr(game, 'show_grid', False):
        off = game.all_sprites.offset
        gsurf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        color = (*GRID_COLOR, GRID_ALPHA)

        start_x = int(( -off.x) // game.grid_size) - 1
        end_x = int((WINDOW_WIDTH - off.x) // game.grid_size) + 1
        for gx in range(start_x, end_x + 1):
            sx = gx * game.grid_size + off.x
            pygame.draw.line(gsurf, color, (sx, 0), (sx, WINDOW_HEIGHT), 1)

        start_y = int(( -off.y) // game.grid_size) - 1
        end_y = int((WINDOW_HEIGHT - off.y) // game.grid_size) + 1
        for gy in range(start_y, end_y + 1):
            sy = gy * game.grid_size + off.y
            pygame.draw.line(gsurf, color, (0, sy), (WINDOW_WIDTH, sy), 1)

        # draw saved click markers (remove expired)
        now = pygame.time.get_ticks()
        new_clicks = []
        for c in game.grid_clicks:
            if c['expiry'] < now:
                continue
            new_clicks.append(c)
            sx, sy = c['screen']
            csx, csy = c['cell_screen']
            gx, gy = c['grid']
            wx, wy = c['world']

            # small cross at clicked point
            pygame.draw.line(gsurf, (255, 200, 0), (sx - 6, sy), (sx + 6, sy), 2)
            pygame.draw.line(gsurf, (255, 200, 0), (sx, sy - 6), (sx, sy + 6), 2)

            # rectangle for the grid cell
            cell_rect = pygame.Rect(csx, csy, game.grid_size, game.grid_size)
            pygame.draw.rect(gsurf, (255, 200, 0), cell_rect, 2)

            # label with world coords and grid indices
            lbl = f"world=({wx},{wy}) grid=({gx},{gy})"
            labsurf = game.grid_font.render(lbl, False, (255, 200, 0))
            # position label near click but keep on-screen
            lx = min(WINDOW_WIDTH - labsurf.get_width() - 8, sx + 12)
            ly = max(8, sy - labsurf.get_height() - 4)
            gsurf.blit(labsurf, (lx, ly))

        game.grid_clicks = new_clicks

        # overlay text with grid size, counts and pixel spans
        num_cols = end_x - start_x + 1
        num_rows = end_y - start_y + 1
        span_x = num_cols * game.grid_size
        span_y = num_rows * game.grid_size
        txt = f"GRID: {game.grid_size}px   cols: {num_cols} ({span_x}px)   rows: {num_rows} ({span_y}px)   (F4 +/-)"
        label = game.grid_font.render(txt, False, COLORS["pure white"])
        gsurf.blit(label, (8, 8))

        game.display_surface.blit(gsurf, (0, 0))

    # If an entry cutscene was playing and it finished, restore control
    if getattr(game, '_entry_cutscene_playing', False):
        try:
            if not (getattr(game, 'cutscene_manager', None) and game.cutscene_manager.is_running()):
                try:
                    game.player.unblock()
                except Exception:
                    pass
                try:
                    game.player.controlled = True
                except Exception:
                    pass
                game._entry_cutscene_playing = False
        except Exception:
            pass

    game.transition_check()
    game.tint_screen(dt)

    pygame.display.update()
