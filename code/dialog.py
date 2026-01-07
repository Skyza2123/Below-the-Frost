from settings import *
from timer import Timer

class DialogTree:
    def __init__(self, character, player, all_sprites, font, end_dialog):
        self.player = player
        self.character = character
        self.font = font
        self.all_sprites = all_sprites
        self.end_dialog = end_dialog

        self.dialog = character.get_dialog() or []
        self.dialog_num = len(self.dialog)
        self.dialog_index = 0

        # debounce so holding space doesn't skip everything
        self.dialog_timer = Timer(200, autostart=True)

        # freeze player while dialog is active
        if self.player:
            self.player.controlled = False
            self.player.direction.update(0, 0)

    def get_current_line(self):
        if 0 <= self.dialog_index < self.dialog_num:
            return self.dialog[self.dialog_index]
        return ""

    def advance(self):
        self.dialog_index += 1
        if self.dialog_index >= self.dialog_num:
            # unfreeze player
            if self.player:
                self.player.controlled = True
                self.player.direction.update(0, 0)
            self.end_dialog(self.character)

    def input(self):
        keys = pygame.key.get_just_pressed()
        if keys[pygame.K_SPACE] and not self.dialog_timer.active:
            self.dialog_timer.activate()
            self.advance()

    def update(self):
        self.dialog_timer.update()
        if self.dialog_num > 0:
            self.input()
        else:
            # no dialog lines -> end immediately
            if self.player:
                self.player.controlled = True
            self.end_dialog(self.character)
