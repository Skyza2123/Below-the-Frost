# ui/overlays/tab_menu.py
from typing import Optional, Callable

from data_characters import CHARACTERS
from settings import *
import pygame


class TabMenu:
    """
    Tab / Journal overlay:
    - toggle with TAB or controller BACK (btn_toggle)
    - supports mouse hover/click on tabs + close X
    - Overview combines Status + Relationships
    - Title shows controlled player name (via title_provider)
    """

    def __init__(
        self,
        *,
        width: int,
        height: int,
        assets,
        btn_confirm: int,
        btn_back: int,
        btn_toggle: Optional[int] = None,
        title_provider: Optional[Callable[[], str]] = None,
        character_id_provider: Optional[Callable[[], str]] = None,  # ✅ ADD THIS
    ):

        self.width = width
        self.height = height
        self.assets = assets

        # shared fonts + overlay
        self.font_title = assets.font_tab_title
        self.font_item = assets.font_tab_item
        self.dim_overlay = assets.dim_overlay

        self.btn_confirm = btn_confirm
        self.btn_back = btn_back
        self.btn_toggle = btn_toggle

        self.title_provider = title_provider

        self.open = False
        self.modal = True

        # mouse hitboxes / hover state
        self._panel_rect: Optional[pygame.Rect] = None
        self._tab_rects: list[pygame.Rect] = []
        self._close_rect: Optional[pygame.Rect] = None
        self.hover_tab: Optional[int] = None
        self.hover_close: bool = False

        # tabs (no Personality)
        self.tabs = ["Overview", "Clues", "Collectibles", "Visions", "Butterflies"]
        self.tab_index = 0

        self.nav_cooldown = 0.0
        self.NAV_DELAY = 0.16

        self.on_action = None  # callable(action_str)

        # related character ID provider (for relationships)
        character_id_provider: Optional[Callable[[], str]] = None,
        self.character_id_provider = character_id_provider
        # previous button state tracking for printing once-per-press
        self._prev_button_state: dict[int, bool] = {}


    # -----------------
    # State
    # -----------------
    def toggle(self):
        self.open = not self.open
        self.nav_cooldown = 0.0
        # reset hover so you don't keep a stale index
        self.hover_tab = None
        self.hover_close = False

    def close(self):
        self.open = False
        self.nav_cooldown = 0.0
        self.hover_tab = None
        self.hover_close = False

    # -----------------
    # Events
    # -----------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        # keyboard toggle
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.toggle()
                return True

            if not self.open:
                return False

            if event.key == pygame.K_ESCAPE:
                self.close()
                return True

        # controller toggle/back
        if event.type == pygame.JOYBUTTONDOWN:
            if self.btn_toggle is not None and event.button == self.btn_toggle:
                self.toggle()
                return True

            if not self.open:
                return False

            if event.button == self.btn_back:
                self.close()
                return True

        # --- mouse support ---
        if not self.open:
            return False

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos

            self.hover_close = bool(self._close_rect and self._close_rect.collidepoint(mx, my))

            self.hover_tab = None
            for i, r in enumerate(self._tab_rects):
                if r.collidepoint(mx, my):
                    self.hover_tab = i
                    break

            # consume motion while overlay open so it doesn't affect world hover logic
            return True

        if event.type == pygame.MOUSEWHEEL:
            # scroll tabs with wheel (only if mouse is over panel; optional but nice)
            mx, my = pygame.mouse.get_pos()
            if self._panel_rect and self._panel_rect.collidepoint(mx, my):
                if event.y > 0:
                    self.tab_index = (self.tab_index - 1) % len(self.tabs)
                elif event.y < 0:
                    self.tab_index = (self.tab_index + 1) % len(self.tabs)
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # close button
            if self._close_rect and self._close_rect.collidepoint(mx, my):
                self.close()
                return True

            # click outside panel closes
            if self._panel_rect and not self._panel_rect.collidepoint(mx, my):
                self.close()
                return True

            # click tabs
            for i, r in enumerate(self._tab_rects):
                if r.collidepoint(mx, my):
                    self.tab_index = i
                    self.nav_cooldown = self.NAV_DELAY
                    return True

            return True  # clicked inside panel; consume

        return False

    # -----------------
    # Update (polling nav)
    # -----------------
    def update(self, dt: float, joystick: Optional[pygame.joystick.Joystick] = None):
        if not self.open:
            return

        self.nav_cooldown = max(0.0, self.nav_cooldown - dt)
        if self.nav_cooldown > 0:
            return

        keys = pygame.key.get_pressed()

        # keyboard: allow Q/E as alternate tab navigation
        if keys[pygame.K_q] or keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.tab_index = (self.tab_index - 1) % len(self.tabs)
            self.nav_cooldown = self.NAV_DELAY
            return

        if keys[pygame.K_e] or keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.tab_index = (self.tab_index + 1) % len(self.tabs)
            self.nav_cooldown = self.NAV_DELAY
            return

        if joystick:
            # D-pad left/right (hat)
            if joystick.get_numhats() > 0:
                hx, _hy = joystick.get_hat(0)
                if hx == -1:
                    self.tab_index = (self.tab_index - 1) % len(self.tabs)
                    self.nav_cooldown = self.NAV_DELAY
                    return
                if hx == 1:
                    self.tab_index = (self.tab_index + 1) % len(self.tabs)
                    self.nav_cooldown = self.NAV_DELAY
                    return

            # left stick X (axis 0)
            if joystick.get_numaxes() > 0:
                ax = joystick.get_axis(0)
                if ax < -0.5:
                    self.tab_index = (self.tab_index - 1) % len(self.tabs)
                    self.nav_cooldown = self.NAV_DELAY
                    return
                if ax > 0.5:
                    self.tab_index = (self.tab_index + 1) % len(self.tabs)
                    self.nav_cooldown = self.NAV_DELAY
                    return

            # controller buttons: LB/RB for tab navigation
            # try reading LB/RB buttons directly (some platforms may raise if index out of range)
            try:
                cur_lb = bool(joystick.get_button(GP_LB))
                prev_lb = bool(self._prev_button_state.get(GP_LB, False))
                if cur_lb and not prev_lb:
                    print(f"JOYBUTTON press joystick LB (button {GP_LB})")
                    self.tab_index = (self.tab_index - 1) % len(self.tabs)
                    self.nav_cooldown = self.NAV_DELAY
                    self._prev_button_state[GP_LB] = True
                    return
                self._prev_button_state[GP_LB] = cur_lb
            except Exception:
                pass

            try:
                cur_rb = bool(joystick.get_button(GP_RB))
                prev_rb = bool(self._prev_button_state.get(GP_RB, False))
                if cur_rb and not prev_rb:
                    print(f"JOYBUTTON press joystick RB (button {GP_RB})")
                    self.tab_index = (self.tab_index + 1) % len(self.tabs)
                    self.nav_cooldown = self.NAV_DELAY
                    self._prev_button_state[GP_RB] = True
                    return
                self._prev_button_state[GP_RB] = cur_rb
            except Exception:
                pass

    # -----------------
    # Draw
    # -----------------
    def draw(self, surface: pygame.Surface):
        if not self.open:
            return

        # dim world
        surface.blit(self.dim_overlay, (0, 0))

        # ------------------------------------------------------------
        # Panel PNG
        # ------------------------------------------------------------
        panel_img = getattr(self.assets, "tab_frame", None)

        if panel_img is None:
            print("TabMenu: assets.tab_frame is None")
            panel = pygame.Rect(80, 40, 1120, 640)
            pygame.draw.rect(surface, (18, 20, 28), panel, border_radius=14)
        else:
            x = (self.width - panel_img.get_width()) // 2
            y = (self.height - panel_img.get_height()) // 2
            surface.blit(panel_img, (x, y))
            panel = pygame.Rect(x, y, panel_img.get_width(), panel_img.get_height())

        self._panel_rect = panel


        # ------------------------------------------------------------
        # Close button (top-right) + hitbox
        # ------------------------------------------------------------
        x_surf = self.font_item.render("X", False, (255, 255, 255) if self.hover_close else (180, 180, 180))
        x_rect = x_surf.get_rect(topright=(panel.x + 1050, panel.y + 26))
        self._close_rect = x_rect.inflate(14, 14)
        surface.blit(x_surf, x_rect.topleft)

        # ------------------------------------------------------------
        # Tabs (text) + mouse hitboxes
        # ------------------------------------------------------------

        name = self.title_provider() if self.title_provider else "Player"

        tab_y = panel.y + 35          # moved up since no big title
        tab_x = panel.x + 30
        tab_gap = 12

        # draw name label (not clickable)
        name_surf = self.font_item.render(f"{name}  •", False, (190, 190, 190))
        surface.blit(name_surf, (tab_x, tab_y))

        tab_x += name_surf.get_width() + 10  # start tabs after the name

        # build tab hitboxes
        self._tab_rects = []

        for i, name in enumerate(self.tabs):
            selected = (i == self.tab_index)
            hovered = (i == self.hover_tab)

            color = (255, 255, 255) if (selected or hovered) else (160, 160, 160)
            t = self.font_item.render(name, False, color)

            text_rect = t.get_rect(topleft=(tab_x, tab_y))
            hit_rect = text_rect.inflate(16, 10)
            self._tab_rects.append(hit_rect)

            if hovered and not selected:
                pygame.draw.rect(surface, (120, 120, 120), hit_rect, 1, border_radius=10)

            surface.blit(t, text_rect.topleft)

            if selected:
                pygame.draw.line(
                    surface, (255, 255, 255),
                    (text_rect.x, text_rect.bottom + 4),
                    (text_rect.right, text_rect.bottom + 4),
                    2
                )

            tab_x = hit_rect.right + tab_gap


        # ------------------------------------------------------------
        # Content area
        # ------------------------------------------------------------
        active = self.tabs[self.tab_index]

        # If your panel art already has a "content box" drawn,
        # you can *skip drawing these rects* and just use the rect for layout.
        content = pygame.Rect(panel.x + 24, panel.y + 78, panel.width - 48, panel.height - 120)


        # optional content box drawing (remove if art already includes it)

        if active == "Overview":
    # --- current character id (do this once) ---
            cid = getattr(self, "character_id_provider", None)
            if callable(cid):
                char_id = cid()
            elif isinstance(cid, str):
                char_id = cid
            else:
                char_id = "raya"

            # ONE combined box inside content — place this box on the LEFT half
            half_w = content.w // 2
            overview_box = pygame.Rect(content.x + 16, content.y + 16, half_w - 32, content.h - 32)

            # draw ONE box (remove these if your PNG already includes this box)
            pygame.draw.rect(surface, (10, 12, 18), overview_box, border_radius=10)
            pygame.draw.rect(surface, (70, 70, 70), overview_box, 2, border_radius=10)

            # two columns INSIDE the same box (no extra borders)
            pad = 18
            col_gap = 8
            # columns live inside the left-half overview box
            avail = (overview_box.w - (pad * 2) - col_gap)
            col_w = (avail // 2)

            traits_col = pygame.Rect(overview_box.x + pad, overview_box.y + pad, col_w, overview_box.h - pad * 2)
            rels_col   = pygame.Rect(traits_col.right + col_gap, overview_box.y + pad, col_w, overview_box.h - pad * 2)

            # divider removed to bring columns closer visually

            # headers
            surface.blit(self.font_item.render("Traits", False, (230, 230, 230)), (traits_col.x, traits_col.y))
            surface.blit(self.font_item.render("Relationships", False, (230, 230, 230)), (rels_col.x, rels_col.y))

            # ----------------------------
            # Traits = stats with bars
            # ----------------------------
            stats = CHARACTERS.get(char_id, {}).get("stats", {})
            order = ["honest", "charitable", "funny", "brave", "romantic", "curious"]

            bar_w = traits_col.w / 3
            bar_h = 10
            y = traits_col.y + 52
            row_h = 50

            for key in order:
                val = int(stats.get(key, 0))
                label = key.capitalize()

                surface.blit(
                    self.font_item.render(f"{label}: {val}/10", False, (200, 200, 200)),
                    (traits_col.x, y)
                )

                y_bar = y + 35
                outline = pygame.Rect(traits_col.x, y_bar, bar_w, bar_h)
                fill = pygame.Rect(traits_col.x, y_bar, int(bar_w * (val / 10.0)), bar_h)

                pygame.draw.rect(surface, (90, 90, 90), outline, 1, border_radius=4)
                pygame.draw.rect(surface, (200, 200, 200), fill, border_radius=4)

                y += row_h
                if y + row_h > traits_col.bottom - 12:
                    break

            # ----------------------------
            # Relationships (fallback-safe)
            # ----------------------------
            who = CHARACTERS.get(char_id, {})

            mode = None
            rsp = getattr(self, "relationship_set_provider", None)
            if callable(rsp):
                mode = rsp()  # expects "prologue" or "story"

            if mode == "prologue":
                rels = who.get("prologue_relationships", {})
            elif mode == "story":
                rels = who.get("story_relationships", {})
            else:
                # default: story if available, else prologue
                rels = who.get("story_relationships") or who.get("prologue_relationships") or {}

            # layout (match Traits sizing/spacing)
            bar_w = rels_col.w / 3
            bar_h = 10
            y = rels_col.y + 52
            row_h = 50

            # sort by value (highest first), and skip self if present
            items = sorted(rels.items(), key=lambda kv: kv[1], reverse=True)
            items = [(k, v) for (k, v) in items if k != char_id]

            if not items:
                surface.blit(self.font_item.render("—", False, (180, 180, 180)), (rels_col.x, y))
            else:
                for other_id, val in items:
                    val = int(val)

                    # show nickname if available, else name, else id
                    other = CHARACTERS.get(other_id, {})
                    display = other.get("nickname") or other.get("name") or other_id.capitalize()

                    surface.blit(
                        self.font_item.render(f"{display}: {val}/10", False, (200, 200, 200)),
                        (rels_col.x, y)
                    )

                    y_bar = y + 35
                    outline = pygame.Rect(rels_col.x, y_bar, bar_w, bar_h)
                    fill = pygame.Rect(rels_col.x, y_bar, int(bar_w * (val / 10.0)), bar_h)

                    pygame.draw.rect(surface, (90, 90, 90), outline, 1, border_radius=4)
                    pygame.draw.rect(surface, (200, 200, 200), fill, border_radius=4)

                    y += row_h
                    if y + row_h > rels_col.bottom - 12:
                        break


            # ----------------------------
            # Right-side portrait placeholder (inside the right half of content)
            # ----------------------------
            right_x = content.x + half_w + 16
            right_w = content.w - half_w - 32
            right_box = pygame.Rect(right_x, content.y + 16, right_w, content.h - 32)

            # draw a subtle panel for the portrait area
            pygame.draw.rect(surface, (12, 14, 18), right_box, border_radius=8)
            pygame.draw.rect(surface, (60, 60, 60), right_box, 2, border_radius=8)

            # portrait frame centered inside right_box
            pad = 24
            frame_w = min(256, right_box.w - pad * 2)
            frame_h = min(320, right_box.h - pad * 2)
            frame_rect = pygame.Rect(
                right_box.x + (right_box.w - frame_w) // 2,
                right_box.y + (right_box.h - frame_h) // 2 - 20,
                frame_w,
                frame_h,
            )

            # try using an asset if provided, otherwise draw a placeholder box with text
            portrait_img = getattr(self.assets, "portrait_placeholder", None)
            if portrait_img:
                img = pygame.transform.scale(portrait_img, (frame_rect.w, frame_rect.h))
                surface.blit(img, frame_rect.topleft)
            else:
                pygame.draw.rect(surface, (40, 44, 50), frame_rect, border_radius=8)
                pygame.draw.rect(surface, (120, 120, 120), frame_rect, 2, border_radius=8)
                txt = self.font_item.render("Portrait", False, (180, 180, 180))
                surface.blit(txt, (frame_rect.centerx - txt.get_width() // 2, frame_rect.centery - txt.get_height() // 2))

