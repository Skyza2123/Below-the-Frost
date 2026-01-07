# ui/ui_assets.py
import pygame
from os.path import join

class UIAssets:
    """
    Loads + stores UI resources once so all overlays can reuse them.
    Keep names stable: overlays will access assets.dialog_panel, assets.dim_overlay, etc.
    """

    def __init__(self, *, width: int, height: int, base_path: str = "graphics", ui_scale: int = 1):
        self.width = width
        self.height = height
        self.base_path = base_path
        self.ui_scale = ui_scale

        # ---------- common overlays ----------
        self.dim_overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self.dim_overlay.fill((0, 0, 0, 140))

        # ---------- fonts ----------
        # (You can centralize all UI fonts here)
        self.font_dialog = pygame.font.Font(join(base_path, "fonts", "PixeloidSans.ttf"), 30)
        self.font_menu_title = pygame.font.Font(join(base_path, "fonts", "PixeloidSans.ttf"), 48)
        self.font_menu_item  = pygame.font.Font(join(base_path, "fonts", "PixeloidSans.ttf"), 28)
        self.font_tab_title  = pygame.font.Font(join(base_path, "fonts", "PixeloidSans.ttf"), 42)
        self.font_tab_item   = pygame.font.Font(join(base_path, "fonts", "PixeloidSans.ttf"), 24)

        # ------ buttons ----
        self.pause_btn = {
            "Resume": pygame.image.load(join(base_path, "ui", "btn_play.png")).convert_alpha(),
            "Settings": pygame.image.load(join(base_path, "ui", "btn_settings.png")).convert_alpha(),
            "Quit to Desktop": pygame.image.load(join(base_path, "ui", "btn_quit.png")).convert_alpha(),
        }



        # ---------- dialog panel ----------
        raw = pygame.image.load(join(base_path, "ui", "dialog_panel.png")).convert_alpha()
        self.dialog_panel = pygame.transform.scale(
            raw, (raw.get_width() * ui_scale, raw.get_height() * ui_scale)
        )

        # ---------- MENU / TAB ART ----------
        raw = pygame.image.load(join(base_path, "ui", "pause_panel.png")).convert_alpha()
        self.pause_panel = raw

        raw = pygame.image.load(join(base_path, "ui", "tab_frame.png")).convert_alpha()
        self.tab_frame = raw    
    

        # ---------- optional: menu / tab art ----------
        # If you have these images, uncomment and set filenames.
        # self.pause_panel = pygame.image.load(join(base_path, "ui", "pause_panel.png")).convert_alpha()
        # self.tab_frame   = pygame.image.load(join(base_path, "ui", "tab_frame.png")).convert_alpha()
