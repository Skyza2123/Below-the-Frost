from settings import *
from support import import_image
from entites import Entity

class AllSprites(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = vector()
        self.shadow_surf = import_image('graphics', 'other', 'shadow')

    def draw(self, player_center):
        self.offset.x = -(player_center[0] - WINDOW_WIDTH / 2)
        self.offset.y = -(player_center[1] - WINDOW_HEIGHT / 2)

        bg_sprites = [sprite for sprite in self if sprite.z < WORLD_LAYERS['main']]
        main_sprites = sorted([sprite for sprite in self if sprite.z == WORLD_LAYERS['main']], key=lambda sprite: sprite.y_sort)
        fg_sprites = [sprite for sprite in self if sprite.z > WORLD_LAYERS['main']]

        for layer in (bg_sprites, main_sprites, fg_sprites):
            for sprite in layer:
                # skip sprites without valid image/rect
                if not getattr(sprite, 'image', None) or not getattr(sprite, 'rect', None):
                    continue

                if isinstance(sprite, Entity):
                    # draw shadow
                    shadow_pos = sprite.rect.topleft + self.offset + vector(46, 110)
                    self.display_surface.blit(self.shadow_surf, shadow_pos)

                self.display_surface.blit(sprite.image, sprite.rect.topleft + self.offset)