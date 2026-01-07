# ui/overlays/pause_menu.py
import pygame
from typing import Optional
from settings import DPAD_BUTTON_UP, DPAD_BUTTON_DOWN


class PauseMenu:
    def __init__(
        self,
        *,
        width: int,
        height: int,
        assets,              # UIAssets bundle
        btn_confirm: int,
        btn_back: int,
        btn_start: int,
    ):
        self.width = width
        self.height = height
        self.assets = assets

        self.font_title = assets.font_menu_title
        self.font_item  = assets.font_menu_item
        self.overlay    = assets.dim_overlay  # reuse shared dim overlay

        self.btn_confirm = btn_confirm
        self.btn_back = btn_back
        self.btn_start = btn_start

        self.open = False
        self.modal = True

        self.stack = ["main"]
        self.index = 0

        self.items = {
            "main": ["Resume", "Settings", "Quit to Desktop"]
        }

        self.nav_cooldown = 0.0
        self.NAV_DELAY = 0.16

        self.on_action = None  # callable(action_str)

        # mouse hitboxes / hover
        self._panel_rect: Optional[pygame.Rect] = None
        self._item_rects: list[pygame.Rect] = []
        self.hover_index: Optional[int] = None

    # -----------------
    # State helpers
    # -----------------
    def toggle(self):
        self.open = not self.open
        self.index = 0
        self.nav_cooldown = 0.0
        self.hover_index = None

    def close(self):
        self.open = False
        self.index = 0
        self.nav_cooldown = 0.0
        self.hover_index = None

    def current_key(self):
        return self.stack[-1]

    def current_items(self):
        return self.items[self.current_key()]

    def move(self, direction: int):
        opts = self.current_items()
        self.index = (self.index + direction) % len(opts)

    # -----------------
    # Actions
    # -----------------
    def activate(self):
        key = self.current_key()
        choice = self.current_items()[self.index]

        if key == "main":
            if choice == "Resume":
                self.close()

            elif choice == "Settings":
                if self.on_action:
                    self.on_action("open_settings")

            elif choice == "Quit to Desktop":
                if self.on_action:
                    self.on_action("quit_desktop")

    def back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.index = 0
        else:
            self.close()

    # -----------------
    # Input (events)
    # -----------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        # keyboard toggle
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.toggle()
                return True

            if not self.open:
                return False

            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate()
                return True

        # controller buttons
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == self.btn_start:
                self.toggle()
                return True

            if not self.open:
                return False

            if event.button == self.btn_confirm:
                self.activate()
                return True

            if event.button == self.btn_back:
                self.back()
                return True
            # treat common DPAD-as-buttons as navigation
            if event.button == DPAD_BUTTON_UP:
                if self.open:
                    self.move(-1)
                    self.nav_cooldown = self.NAV_DELAY
                    return True
            if event.button == DPAD_BUTTON_DOWN:
                if self.open:
                    self.move(+1)
                    self.nav_cooldown = self.NAV_DELAY
                    return True

        # --- mouse support ---
        if not self.open:
            return False

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hover_index = None
            for i, r in enumerate(self._item_rects):
                if r.collidepoint(mx, my):
                    self.hover_index = i
                    break

            # NOTE: do NOT sync mouse hover to the selected index here.
            # Hover only shows a visual hover state; keyboard/controller
            # navigation will change `self.index`. Clicking an item will
            # still set `self.index` and activate it.

            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._panel_rect and self._panel_rect.collidepoint(mx, my):
                if event.y > 0:
                    self.move(-1)
                elif event.y < 0:
                    self.move(+1)
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # click outside closes
            if self._panel_rect and not self._panel_rect.collidepoint(mx, my):
                self.close()
                return True

            # joystick hat (D-PAD) events
            if event.type == pygame.JOYHATMOTION:
                # value is (x, y)
                if not self.open:
                    return False
                _, hy = event.value
                if hy == 1:
                    self.move(-1)
                    self.nav_cooldown = self.NAV_DELAY
                    return True
                if hy == -1:
                    self.move(+1)
                    self.nav_cooldown = self.NAV_DELAY
                    return True

            # joystick axis (e.g., left stick Y) navigation as events
            if event.type == pygame.JOYAXISMOTION:
                if not self.open:
                    return False
                # axis 1 is commonly left stick Y
                if event.axis == 1:
                    if event.value < -0.5:
                        self.move(-1)
                        self.nav_cooldown = self.NAV_DELAY
                        return True
                    if event.value > 0.5:
                        self.move(+1)
                        self.nav_cooldown = self.NAV_DELAY
                        return True

            # click an item activates
            for i, r in enumerate(self._item_rects):
                if r.collidepoint(mx, my):
                    self.index = i
                    self.activate()
                    return True

            return True  # clicked inside panel; consume

        return False

    # -----------------
    # Input (polling) for navigation
    # -----------------
    def update(self, dt: float, joystick: Optional[pygame.joystick.Joystick] = None):
        if not self.open:
            return

        self.nav_cooldown = max(0.0, self.nav_cooldown - dt)
        if self.nav_cooldown > 0:
            return

        # keyboard navigation
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.move(-1)
            self.nav_cooldown = self.NAV_DELAY
            return
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.move(+1)
            self.nav_cooldown = self.NAV_DELAY
            return

        # controller navigation (d-pad hat / left stick Y)
        if joystick:
            if joystick.get_numhats() > 0:
                hx, hy = joystick.get_hat(0)
                if hy == 1:
                    self.move(-1)
                    self.nav_cooldown = self.NAV_DELAY
                    return
                if hy == -1:
                    self.move(+1)
                    self.nav_cooldown = self.NAV_DELAY
                    return

            if joystick.get_numaxes() > 1:
                ay = joystick.get_axis(1)
                if ay < -0.5:
                    self.move(-1)
                    self.nav_cooldown = self.NAV_DELAY
                    return
                if ay > 0.5:
                    self.move(+1)
                    self.nav_cooldown = self.NAV_DELAY
                    return

    # -----------------
    # Draw
    # -----------------
    def draw(self, surface: pygame.Surface):
        if not self.open:
            return

        surface.blit(self.overlay, (0, 0))

        # ------------------------------------------------------------
        # Panel PNG (instead of drawing rect)
        # ------------------------------------------------------------
        panel_img = getattr(self.assets, "pause_panel", None)

        if panel_img is None:
            # fallback to old rectangle style if PNG not loaded yet
            panel_w, panel_h = 520, 360
            panel = pygame.Rect(
                (self.width - panel_w) // 2,
                (self.height - panel_h) // 2,
                panel_w,
                panel_h,
            )
            self._panel_rect = panel
            pygame.draw.rect(surface, (20, 25, 35), panel, border_radius=14)
            pygame.draw.rect(surface, (220, 220, 220), panel, 3, border_radius=14)
        else:
            px = (self.width - panel_img.get_width()) // 2
            py = (self.height - panel_img.get_height()) // 2
            surface.blit(panel_img, (px, py))
            panel = pygame.Rect(px, py, panel_img.get_width(), panel_img.get_height())
            self._panel_rect = panel


        # ------------------------------------------------------------
        # Buttons (PNG) + hitboxes
        # ------------------------------------------------------------
        opts = self.current_items()
        self._item_rects = []

        # Buttons layout offsets inside panel
        # Adjust these once to match your art.
        btn_gap = 100
        btn_start_y = panel.y + 120

        # If you have a consistent button size (recommended), we can center them cleanly.
        # We’ll use the "Resume" button as reference if present.
        btn_dict = getattr(self.assets, "pause_btn", {})
        ref = btn_dict.get("Resume") or (btn_dict[opts[0]] if opts and opts[0] in btn_dict else None)

        # fallback: if no button images exist, render text as before
        if not btn_dict or ref is None:
            # ----- old text-based list fallback -----
            start_y = panel.y + 120
            line_h = 44
            for i, label in enumerate(opts):
                selected = (i == self.index)
                hovered = (self.hover_index == i)

                color = (255, 255, 255) if selected else (170, 170, 170)
                txt_surf = self.font_item.render(label, False, color)

                x = panel.centerx - txt_surf.get_width() // 2
                y = start_y + i * line_h

                draw_rect = pygame.Rect(x, y, txt_surf.get_width(), txt_surf.get_height())
                hit_rect = draw_rect.inflate(80, 18)
                self._item_rects.append(hit_rect)

                if hovered and not selected:
                    pygame.draw.rect(surface, (120, 120, 120), hit_rect, 1, border_radius=10)

                # draw glow for hover only (text glow)
                if hovered:
                    glow_color = (200, 180, 120)
                    glow_surf = self.font_item.render(label, False, glow_color)
                    glow_surf.set_alpha(60)
                    offsets = [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]
                    for ox, oy in offsets:
                        surface.blit(glow_surf, (x+ox, y+oy))

                # draw stronger outline for selection (no glow)
                if selected:
                    pygame.draw.rect(surface, (220, 220, 220), hit_rect, 2, border_radius=10)

                surface.blit(txt_surf, (x, y))
            return

        # ----- PNG button layout -----
        btn_w, btn_h = ref.get_width(), ref.get_height()
        total_h = len(opts) * btn_h + (len(opts) - 1) * btn_gap
        y0 = panel.y + 120  # top anchor (matches your old layout)
        # optionally center the stack vertically inside panel content area:
        # y0 = panel.centery - total_h // 2

        for i, label in enumerate(opts):
            selected = (i == self.index)
            hovered = (self.hover_index == i)

            # pick the right button image
            surf_btn = btn_dict.get(label)

            # optional variants
            btn_hover = getattr(self.assets, "pause_btn_hover", {})
            btn_sel = getattr(self.assets, "pause_btn_selected", {})

            if selected and label in btn_sel:
                surf_btn = btn_sel[label]
            # prefer hover art when hovered OR when selected but no selected-art available
            elif (hovered or selected) and label in btn_hover:
                surf_btn = btn_hover[label]

            if surf_btn is None:
                # if a specific button image is missing, fall back to text
                txt = self.font_item.render(label, False, (255, 255, 255))
                surf_btn = txt

            x = panel.centerx - surf_btn.get_width() // 2
            y = y0 + i * (btn_h + btn_gap)

            # clickable rect (slightly inflated) - compute early so outlines can use it
            hit_rect = pygame.Rect(x, y, surf_btn.get_width(), surf_btn.get_height()).inflate(10, 10)
            self._item_rects.append(hit_rect)

            # draw button
            surface.blit(surf_btn, (x, y))

            # draw label text over button; support glowing selected text
            txt_color = (255, 255, 255) if selected else (200, 200, 200)
            txt_surf = self.font_item.render(label, False, txt_color)
            tx = panel.centerx - txt_surf.get_width() // 2
            ty = y + (surf_btn.get_height() - txt_surf.get_height()) // 2
            # glow for hover only (text glow)
            if hovered:
                glow_color = (220, 200, 140)
                glow_surf = self.font_item.render(label, False, glow_color)
                glow_surf.set_alpha(60)
                offsets = [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,2),(-2,2),(2,-2)]
                for ox, oy in offsets:
                    surface.blit(glow_surf, (tx+ox, ty+oy))

            # if selected, draw selection outline (no glow)
            if selected and (not btn_sel or label not in btn_sel):
                pygame.draw.rect(surface, (255, 235, 180), hit_rect, 2, border_radius=10)
            surface.blit(txt_surf, (tx, ty))

            # optional: if you *don’t* have hover art, draw a subtle outline
            if hovered and not selected and (not btn_hover or label not in btn_hover):
                pygame.draw.rect(surface, (160, 160, 160), hit_rect, 1, border_radius=10)

            # if selected but no selected-art exists, draw a stronger selection outline
            if selected and (not btn_sel or label not in btn_sel):
                pygame.draw.rect(surface, (220, 220, 220), hit_rect, 2, border_radius=10)

        # ------------------------------------------------------------
        # Hint footer (optional)
        # ------------------------------------------------------------
        hint = "Enter/A: Select    Esc/Start: Toggle    B: Back"
        h = self.font_item.render(hint, False, (150, 150, 150))
        surface.blit(h, (panel.centerx - h.get_width() // 2, panel.bottom - 52))

