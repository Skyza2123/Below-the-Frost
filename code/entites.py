# entites.py
from __future__ import annotations

import pygame
from settings import *  # expects: vector (pygame.math.Vector2), WORLD_LAYERS, ANIMATION_SPEED, TILE_SIZE, etc.


class Entity(pygame.sprite.Sprite):
    """
    animations format:
        animations[action][direction] = [Surface, Surface, ...]
    where action in {"idle","walk",...}
    and direction in {"down","up","left","right"} (or whatever you imported)
    """

    def __init__(self, pos, frames, groups, facing_direction="down"):
        super().__init__(groups)

        self.z = WORLD_LAYERS["main"]

        # graphics / animation
        self.animations = frames
        self.action = "idle"
        self.facing_direction = facing_direction

        self.frame_index = 0.0
        self.anim_speed = ANIMATION_SPEED
        self._last_action = self.action
        self._last_facing = self.facing_direction

        # movement
        self.direction = vector()
        # base walking speed (pixels/sec). Running speed will be higher.
        # Desired: walk = 150, run = 250
        self.base_speed = 150
        self.run_multiplier = 250 / 150
        self.is_running = False
        self.speed = self.base_speed
        self.blocked = False  # for cutscenes, etc.

        # sprite image + rect
        self.image = self.animations["idle"][self.facing_direction][0]
        self.rect = self.image.get_rect(center=pos)

        # -----------------------------
        # CHEST HITBOX (authoritative)
        # -----------------------------
        # Offset is measured from the sprite's MIDBOTTOM (feet) to the chest center.
        # Tune this so the red box sits on the chest in your art.
        self.chest_offset = vector(0, -self.rect.height * 0.5)

        # Chest box size (tight to torso)
        self.hitbox = pygame.Rect(0, 0, 30, 50)

        # Place hitbox at chest based on current rect position
        self.hitbox.center = vector(self.rect.midbottom) + self.chest_offset

        # Float position tracks hitbox center (NOT rect)
        self.pos = vector(self.hitbox.center)

        # Make rect consistent immediately (prevents first-frame snapping)
        self.sync_rect_from_hitbox()

        # used for y-sorting draw order
        self.y_sort = self.rect.centery

    # -----------------------------
    # Helpers
    # -----------------------------
    def sync_rect_from_hitbox(self):
        """Keep sprite positioned from chest hitbox (one source of truth)."""
        self.rect.midbottom = vector(self.hitbox.center) - self.chest_offset

    def update_facing(self):
        """Update facing direction from movement vector."""
        if self.direction.length_squared() == 0:
            return

        # If you want stable facing on diagonals (no jitter), keep this:
        if self.direction.x != 0 and self.direction.y != 0:
            return

        if self.direction.x != 0:
            self.facing_direction = "right" if self.direction.x > 0 else "left"
        else:
            self.facing_direction = "down" if self.direction.y > 0 else "up"

    def animate(self, dt: float):
        moving = self.direction.length_squared() > 0
        running = getattr(self, 'is_running', False) and moving

        # prefer a 'run' animation if available while running, otherwise fall back to 'walk'
        if running and "run" in self.animations:
            self.action = "run"
        else:
            self.action = "walk" if moving else "idle"

        # make run animations play faster for feel (only when running)
        self.anim_speed = ANIMATION_SPEED * (1.5 if running else 1.0)

        # reset frame on state change
        if self.action != self._last_action or self.facing_direction != self._last_facing:
            self.frame_index = 0.0
            self._last_action = self.action
            self._last_facing = self.facing_direction

        frames = self.animations[self.action][self.facing_direction]
        self.frame_index += self.anim_speed * dt
        self.image = frames[int(self.frame_index) % len(frames)]

    def change_facing_direction(self, target_pos):
        """Change facing direction to look at `target_pos`."""
        relation = vector(target_pos) - vector(self.rect.center)
        if abs(relation.x) > abs(relation.y):
            self.facing_direction = "right" if relation.x > 0 else "left"
        else:
            self.facing_direction = "down" if relation.y > 0 else "up"

    def block(self, duration: float | None = None):
        """Block movement. If `duration` is provided, unblock after that many seconds."""
        self.blocked = True
        self.direction = vector(0, 0)
        # force idle animation immediately
        self.action = "idle"
        self.frame_index = 0.0
        self._last_action = self.action
        self._last_facing = self.facing_direction
        # set image to first idle frame for current facing
        self.image = self.animations.get("idle", {}).get(self.facing_direction, [self.image])[0]
        if duration is not None:
            self.block_timer = float(duration)
        else:
            self.block_timer = 0.0

    def unblock(self):
        self.blocked = False
        # clear any timer
        self.block_timer = 0.0
        # reset frame index so animation resumes cleanly
        self.frame_index = 0.0
        self._last_action = None
        # reset frame index so animation resumes cleanly
        self.frame_index = 0.0
        self._last_action = None


class Character(Entity):
    """Non-player character.

    Note: we store `character_id` so cutscenes can target NPCs by id.
    """

    def __init__(self, pos, frames, groups, facing_direction, character_data, character_id: str | None = None):
        super().__init__(pos, frames, groups, facing_direction)
        self.character_data = character_data
        self.character_id = character_id
    
    def get_dialog(self):
        key = "defeated" if self.character_data["defeated"] else "default"
        return self.character_data["dialog"][key]


    def update(self, dt):
        self.animate(dt)


class Player(Entity):
    def __init__(self, pos, frames, groups, facing_direction="down", collision_sprites=None):
        super().__init__(pos, frames, groups, facing_direction)

        # allow passing collision sprites explicitly or as the 2nd element of `groups`
        if collision_sprites is None and isinstance(groups, (tuple, list)) and len(groups) > 1:
            self.collision_sprites = groups[1]
        else:
            self.collision_sprites = collision_sprites or pygame.sprite.Group()

        # for handoff-control systems
        self.controlled = True

        # when True, Player.input() will not override direction/speed.
        # Used by cutscenes to drive movement.
        self.input_disabled = False

    def input(self):
        # cutscenes can drive direction/speed directly
        if getattr(self, 'input_disabled', False):
            return

        keys = pygame.key.get_pressed()
        # keyboard input (support arrows + WASD)
        kb_x = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) + (keys[pygame.K_d] - keys[pygame.K_a])
        kb_y = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) + (keys[pygame.K_s] - keys[pygame.K_w])

        # joystick input (left stick + dpad/hat)
        joy_x = 0.0
        joy_y = 0.0
        joy_run = False
        if pygame.joystick.get_count() > 0:
            joy = pygame.joystick.Joystick(GAMEPAD_INDEX)
            # hat (dpad) - prefer hat if pressed
            try:
                hat = joy.get_hat(GP_HAT)
            except Exception:
                hat = (0, 0)

            if hat and (hat[0] != 0 or hat[1] != 0):
                joy_x = float(hat[0])
                # hat's y: 1 is up, -1 is down -> invert to match screen coords (down positive)
                joy_y = float(-hat[1])
            else:
                # left stick axes (0,1) - ignore right stick
                try:
                    ax = joy.get_axis(0)
                    ay = joy.get_axis(1)
                except Exception:
                    ax = 0.0
                    ay = 0.0
                # apply deadzone
                joy_x = ax if abs(ax) > GAMEPAD_DEADZONE else 0.0
                joy_y = ay if abs(ay) > GAMEPAD_DEADZONE else 0.0

                # some controllers map D-PAD to buttons instead of a hat; check them if no hat/axis input
                try:
                    if joy_x == 0.0 and joy_y == 0.0:
                        up = bool(joy.get_button(DPAD_BUTTON_UP))
                        down = bool(joy.get_button(DPAD_BUTTON_DOWN))
                        left = bool(joy.get_button(DPAD_BUTTON_LEFT))
                        right = bool(joy.get_button(DPAD_BUTTON_RIGHT))
                        if up or down or left or right:
                            # map to -1/1 values (note: screen y positive is down, so invert up)
                            joy_x = -1.0 if left else (1.0 if right else 0.0)
                            joy_y = -1.0 if up else (1.0 if down else 0.0)
                except Exception:
                    pass

            # LB or configured run button to run
            try:
                joy_run = bool(joy.get_button(GP_LB) or joy.get_button(GP_RUN_BUTTON))
            except Exception:
                joy_run = False

        # combine inputs (keyboard digital + joystick analog)
        v = vector(kb_x + joy_x, kb_y + joy_y)
        self.direction = v.normalize() if v.length_squared() > 0 else v

        # running when LB or Shift is held and there's movement input
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        self.is_running = bool((shift or joy_run) and self.direction.length_squared() > 0)

        # adjust speed according to running state
        self.speed = self.base_speed * (self.run_multiplier if self.is_running else 1.0)

        # (no debug prints)

    def collisions(self, axis: str, delta: float, prev_hitbox: pygame.Rect) -> bool:
        """
        Standard axis-separated collision resolution using hitbox.
        Expects colliders to have .hitbox (Rect). If not, it falls back to .rect.
        """
        # swept area between previous and current hitbox to catch passing collisions
        swept = prev_hitbox.union(self.hitbox)

        # collect relevant colliders first (handles multiple overlapping objects)
        colliders = []
        for sprite in self.collision_sprites:
            if sprite is self:
                continue

            other = getattr(sprite, "hitbox", None)
            if other is None:
                other = getattr(sprite, "rect", None)
            if other is None:
                continue

            # ignore colliders that are effectively the player's own hitbox
            if other is self.hitbox or (other.size == self.hitbox.size and other.center == self.hitbox.center):
                continue

            # consider colliders that intersect the swept path (prev->current)
            if not other.colliderect(swept):
                continue

            # if there's no movement along this axis, skip
            if delta == 0:
                continue

            # require overlap on the orthogonal axis to avoid corner-only collisions
            if axis == "horizontal":
                overlap = min(self.hitbox.bottom, other.bottom) - max(self.hitbox.top, other.top)
                orthogonal_size = self.hitbox.height
            else:  # vertical
                overlap = min(self.hitbox.right, other.right) - max(self.hitbox.left, other.left)
                orthogonal_size = self.hitbox.width

            # minimum overlap threshold (pixels) to consider a solid collision
            min_overlap = max(4, int(orthogonal_size * 0.2))
            if overlap < min_overlap:
                # only touching at a corner or very slight edge — ignore to prevent clipping
                continue

            colliders.append(other)

        if not colliders:
            return False

        # collision(s) detected along this axis
        return True

    def move(self, dt: float):
        # normalize so diagonals aren't faster
        if self.direction.length_squared() > 0:
            self.direction = self.direction.normalize()

        # compute movement deltas
        dx = self.direction.x * self.speed * dt
        dy = self.direction.y * self.speed * dt

        # If the player is holding vertical input, always resolve vertical first
        # This makes it easier to slide off objects while holding up/down.
        process_vertical_first = (dy != 0)

        # small nudge away when canceling movement due to collision
        nudge = 3

        if process_vertical_first:
            # -------- Y axis --------
            prev = self.hitbox.copy()
            prev_pos_y = float(self.pos.y)
            self.pos.y += dy
            self.hitbox.centery = round(self.pos.y)
            collided = self.collisions("vertical", dy, prev)
            if collided:
                # revert movement on this axis
                self.hitbox = prev
                self.pos.y = prev_pos_y
                # small nudge away opposite to movement direction
                if dy > 0:
                    self.pos.y -= nudge
                elif dy < 0:
                    self.pos.y += nudge
                self.hitbox.centery = round(self.pos.y)
            else:
                self.pos.y = self.hitbox.centery

            # -------- X axis --------
            prev = self.hitbox.copy()
            prev_pos_x = float(self.pos.x)
            self.pos.x += dx
            self.hitbox.centerx = round(self.pos.x)
            collided = self.collisions("horizontal", dx, prev)
            if collided:
                self.hitbox = prev
                self.pos.x = prev_pos_x
                if dx > 0:
                    self.pos.x -= nudge
                elif dx < 0:
                    self.pos.x += nudge
                self.hitbox.centerx = round(self.pos.x)
            else:
                self.pos.x = self.hitbox.centerx
        else:
            # -------- X axis --------
            prev = self.hitbox.copy()
            prev_pos_x = float(self.pos.x)
            self.pos.x += dx
            self.hitbox.centerx = round(self.pos.x)
            collided = self.collisions("horizontal", dx, prev)
            if collided:
                self.hitbox = prev
                self.pos.x = prev_pos_x
                if dx > 0:
                    self.pos.x -= nudge
                elif dx < 0:
                    self.pos.x += nudge
                self.hitbox.centerx = round(self.pos.x)
            else:
                self.pos.x = self.hitbox.centerx  # snap float back after collision correction

            # -------- Y axis --------
            prev = self.hitbox.copy()
            prev_pos_y = float(self.pos.y)
            self.pos.y += dy
            self.hitbox.centery = round(self.pos.y)
            collided = self.collisions("vertical", dy, prev)
            if collided:
                self.hitbox = prev
                self.pos.y = prev_pos_y
                if dy > 0:
                    self.pos.y -= nudge
                elif dy < 0:
                    self.pos.y += nudge
                self.hitbox.centery = round(self.pos.y)
            else:
                self.pos.y = self.hitbox.centery

        # sprite follows chest hitbox
        self.sync_rect_from_hitbox()

    def update(self, dt: float):
        # handle blocking timer if present
        if getattr(self, 'blocked', False) and getattr(self, 'block_timer', 0) > 0:
            self.block_timer -= dt
            if self.block_timer <= 0:
                self.unblock()

        if not self.blocked:
            if self.controlled:
                self.input()
            else:
                self.direction.update(0, 0)

            self.move(dt)

        self.animate(dt)

        self.update_facing()

        # keep y-sort correct after movement
        self.y_sort = self.rect.centery
