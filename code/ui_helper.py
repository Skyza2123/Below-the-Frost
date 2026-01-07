import pygame

def draw_dialog_panel_full_width(screen, panel_src, *, bottom_y, height, border=12):
    """
    panel_src: the cropped panel image (176x62)
    border: how many pixels are "corner/cap" width on left/right
    height: final height in pixels (use integer scaling of the source height)
    """
    src_w, src_h = panel_src.get_width(), panel_src.get_height()
    scale = height // src_h  # integer scale only
    if scale < 1:
        scale = 1
        height = src_h

    cap_w = border
    mid_w = src_w - border * 2

    left  = panel_src.subsurface(pygame.Rect(0, 0, cap_w, src_h))
    mid   = panel_src.subsurface(pygame.Rect(border, 0, mid_w, src_h))
    right = panel_src.subsurface(pygame.Rect(src_w - cap_w, 0, cap_w, src_h))

    # scale (nearest) — crisp
    left_s  = pygame.transform.scale(left,  (cap_w * scale, height))
    mid_s   = pygame.transform.scale(mid,   (mid_w * scale, height))
    right_s = pygame.transform.scale(right, (cap_w * scale, height))

    W = screen.get_width()
    x = 0

    # left cap
    screen.blit(left_s, (x, bottom_y))
    x += left_s.get_width()

    # tiled middle
    end_x = W - right_s.get_width()
    while x < end_x:
        screen.blit(mid_s, (x, bottom_y))
        x += mid_s.get_width()

    # right cap (flush to the right)
    screen.blit(right_s, (W - right_s.get_width(), bottom_y))
