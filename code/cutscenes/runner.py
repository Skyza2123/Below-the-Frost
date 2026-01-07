"""cutscenes/runner.py

This module provides a small, *data-driven* cutscene system.

The vibe is intentionally Stardew-like:
  - The world/map keeps rendering underneath.
  - A cutscene runner temporarily takes control (locks player input).
  - The cutscene advances through a simple script.

The script format matches `data/scenes/data_cutscenes.py`:

    {"type": "set_pos", "character": "raya", "pos": (220, 320)}
    {"type": "move_to", "character": "raya", "to": (220, 140), "run": True, "arrive_px": 4}
    {"type": "wait", "ms": 150}
    {"type": "face", "character": "raya", "dir": "left"}
    {"type": "end"}

Supported commands (minimal, safe):
  - set_pos(character, pos)
  - face(character, dir)
  - move_to(character, to, run=False, arrive_px=4)
  - wait(ms)
  - set_action(character, action, ms=0)   (best for idle holds)
  - say(who, text)                        (optional subtitle; SPACE/A to advance)
  - end
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import os
from os.path import join

import pygame


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _vec2(xy) -> pygame.math.Vector2:
    return pygame.math.Vector2(float(xy[0]), float(xy[1]))


def resolve_entity(ctx: dict[str, Any], who: str | None):
    """Resolve a character name/id to an in-world sprite.

    Rules:
      - "player" always maps to ctx['player']
      - if ctx['player'].character_id matches `who`, treat it as player
      - otherwise search ctx['character_sprites'] for .character_id == who
    """

    if not ctx:
        return None

    player = ctx.get("player")
    if who in (None, "player"):
        return player

    try:
        if player is not None and getattr(player, "character_id", None) == who:
            return player
    except Exception:
        pass

    for ch in ctx.get("character_sprites", []) or []:
        try:
            if getattr(ch, "character_id", None) == who:
                return ch
        except Exception:
            continue

    return None


def _set_entity_center(ent, xy: tuple[float, float]):
    """Move an entity by its authoritative hitbox center if present."""
    x, y = float(xy[0]), float(xy[1])

    if hasattr(ent, "hitbox") and ent.hitbox is not None:
        try:
            ent.hitbox.center = (int(x), int(y))
            if hasattr(ent, "pos"):
                ent.pos.update(x, y)
            if hasattr(ent, "sync_rect_from_hitbox"):
                ent.sync_rect_from_hitbox()
            else:
                ent.rect.center = ent.hitbox.center
        except Exception:
            # fallback
            ent.rect.center = (int(x), int(y))
    else:
        ent.rect.center = (int(x), int(y))

    try:
        ent.y_sort = ent.rect.centery
    except Exception:
        pass


def _get_entity_center(ent) -> pygame.math.Vector2:
    if hasattr(ent, "hitbox") and ent.hitbox is not None:
        try:
            cx, cy = ent.hitbox.center
            return pygame.math.Vector2(float(cx), float(cy))
        except Exception:
            pass
    cx, cy = ent.rect.center
    return pygame.math.Vector2(float(cx), float(cy))


def _face_from_delta(ent, delta: pygame.math.Vector2):
    try:
        if abs(delta.x) > abs(delta.y):
            ent.facing_direction = "right" if delta.x > 0 else "left"
        else:
            ent.facing_direction = "down" if delta.y > 0 else "up"
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Cutscene types
# -----------------------------------------------------------------------------


@dataclass
class Subtitle:
    who: str
    text: str


class VideoCutscene:
    """Plays a list of images fullscreen (simple storyboard / comic panels)."""

    def __init__(self, name: str, data: dict[str, Any]):
        self.name = name
        self.data = data or {}
        self.frames: list[pygame.Surface] = []
        self.fps = float(self.data.get("fps", 30))
        self.loop = bool(self.data.get("loop", False))
        self.frame_index = 0
        self.frame_timer = 1.0 / max(0.0001, self.fps)
        self.done = False

        imgs = self.data.get("images") or ([self.data.get("image")] if self.data.get("image") else [])
        for p in imgs:
            if not p:
                continue
            try:
                path = p
                if not os.path.isabs(path):
                    path = join(os.getcwd(), path)
                surf = pygame.image.load(path).convert_alpha()
                self.frames.append(surf)
            except Exception:
                continue

    def start(self, ctx: dict[str, Any]):
        self.ctx = ctx or {}
        self.frame_index = 0
        self.frame_timer = 1.0 / max(0.0001, self.fps)
        self.done = False

    def update(self, dt: float, ctx: dict[str, Any]):
        if self.done:
            return
        if not self.frames:
            self.done = True
            return

        self.frame_timer -= dt
        if self.frame_timer <= 0:
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                if self.loop:
                    self.frame_index = 0
                else:
                    self.done = True
                    return
            self.frame_timer = 1.0 / max(0.0001, self.fps)

    def draw(self, screen: pygame.Surface, window_size: tuple[int, int]):
        if not self.frames:
            return
        idx = int(self.frame_index) % len(self.frames)
        surf = self.frames[idx]

        sw, sh = surf.get_size()
        ww, wh = window_size
        if sw <= 0 or sh <= 0:
            return
        scale = min(ww / sw, wh / sh)
        target = pygame.transform.smoothscale(surf, (max(1, int(sw * scale)), max(1, int(sh * scale))))
        tx = (ww - target.get_width()) // 2
        ty = (wh - target.get_height()) // 2
        screen.blit(target, (tx, ty))


class ScriptCutscene:
    """Runs a data-cutscene dict with a simple command list."""

    def __init__(self, name: str, data: dict[str, Any]):
        self.name = name
        self.data = data or {}
        self.script: list[dict[str, Any]] = list(self.data.get("script", []))

        self.ip = 0
        self.done = False

        self._timer = 0.0
        self._move_cmd: Optional[dict[str, Any]] = None
        self._subtitle: Optional[Subtitle] = None
        self._waiting_for_advance = False

    # --- public API ---
    def start(self, ctx: dict[str, Any]):
        self.ctx = ctx or {}
        self.ip = 0
        self.done = False
        self._timer = 0.0
        self._move_cmd = None
        self._subtitle = None
        self._waiting_for_advance = False

    def has_subtitle(self) -> bool:
        return self._subtitle is not None

    def get_subtitle(self) -> Optional[Subtitle]:
        return self._subtitle

    def advance(self):
        """Advance a blocking 'say' command."""
        if self._waiting_for_advance:
            self._waiting_for_advance = False
            self._subtitle = None

    # --- engine ---
    def update(self, dt: float, ctx: dict[str, Any]):
        if self.done:
            return

        self.ctx = ctx or self.ctx or {}

        # blocking subtitle
        if self._waiting_for_advance:
            return

        # timed waits
        if self._timer > 0:
            self._timer = max(0.0, self._timer - dt)
            return

        # movement
        if self._move_cmd is not None:
            self._step_move(dt)
            return

        # execute immediate commands until we hit a blocking command
        while not self.done and self.ip < len(self.script):
            cmd = self.script[self.ip] or {}
            self.ip += 1
            ctype = cmd.get("type")

            if ctype == "set_pos":
                who = cmd.get("character")
                ent = resolve_entity(self.ctx, who)
                if ent is not None:
                    _set_entity_center(ent, cmd.get("pos", (0, 0)))
                continue

            if ctype == "face":
                who = cmd.get("character")
                ent = resolve_entity(self.ctx, who)
                if ent is not None:
                    try:
                        ent.facing_direction = cmd.get("dir", ent.facing_direction)
                    except Exception:
                        pass
                continue

            if ctype == "wait":
                ms = float(cmd.get("ms", 0))
                self._timer = max(0.0, ms / 1000.0)
                return

            if ctype == "set_action":
                # best used for "idle" holds; most entities' animate() will overwrite
                who = cmd.get("character")
                ent = resolve_entity(self.ctx, who)
                if ent is not None:
                    try:
                        ent.action = cmd.get("action", "idle")
                        ent.frame_index = 0.0
                    except Exception:
                        pass
                ms = float(cmd.get("ms", 0))
                if ms > 0:
                    self._timer = ms / 1000.0
                    return
                continue

            if ctype == "move_to":
                self._move_cmd = cmd
                return

            if ctype == "say":
                who = str(cmd.get("who") or cmd.get("character") or "")
                text = str(cmd.get("text") or "")
                self._subtitle = Subtitle(who=who, text=text)
                self._waiting_for_advance = True
                return

            if ctype == "end":
                self.done = True
                return

            # unknown command: ignore safely
            continue

        # fell off the end
        if self.ip >= len(self.script):
            self.done = True

    def _step_move(self, dt: float):
        cmd = self._move_cmd or {}
        who = cmd.get("character")
        ent = resolve_entity(self.ctx, who)
        if ent is None:
            self._move_cmd = None
            return

        target = cmd.get("to")
        if not target:
            self._move_cmd = None
            return

        run = bool(cmd.get("run", False))
        arrive_px = float(cmd.get("arrive_px", 4))

        cur = _get_entity_center(ent)
        tgt = _vec2(target)
        delta = tgt - cur
        dist = float(delta.length())

        if dist <= arrive_px:
            # stop
            try:
                ent.direction.update(0, 0)
            except Exception:
                pass
            try:
                ent.is_running = False
            except Exception:
                pass
            self._move_cmd = None
            return

        if dist > 0:
            direction = delta.normalize()
        else:
            direction = pygame.math.Vector2(0, 0)

        # --- Player: let Player.update() handle collisions + movement ---
        is_player = False
        try:
            is_player = bool(getattr(ent, "__class__", None) and ent.__class__.__name__ == "Player")
        except Exception:
            is_player = False

        if is_player:
            try:
                ent.direction.update(direction.x, direction.y)
                ent.is_running = run
                base = float(getattr(ent, "base_speed", 150))
                mult = float(getattr(ent, "run_multiplier", (250 / 150)))
                ent.speed = base * (mult if run else 1.0)
            except Exception:
                pass
            _face_from_delta(ent, delta)
            return

        # --- NPCs: move manually (they don't have Player.move/collisions) ---
        speed = 250.0 if run else 150.0
        step = min(dist, speed * dt)
        new_pos = cur + direction * step

        try:
            ent.direction.update(direction.x, direction.y)
            ent.is_running = run
        except Exception:
            pass

        _face_from_delta(ent, delta)
        _set_entity_center(ent, (new_pos.x, new_pos.y))


# -----------------------------------------------------------------------------
# Manager (what Game/renderer talks to)
# -----------------------------------------------------------------------------


class CutSceneManager:
    def __init__(self, screen: Optional[pygame.Surface] = None):
        self.completed: set[str] = set()
        self.cutscene: Any = None
        self.running = False
        self.screen = screen
        self.window_size = screen.get_size() if screen else (0, 0)
        self.ctx: dict[str, Any] = {}

        # player state snapshot during a running cutscene
        self._player_prev: dict[str, Any] = {}

    def set_screen(self, screen: pygame.Surface):
        self.screen = screen
        self.window_size = screen.get_size() if screen else (0, 0)

    def set_context(self, ctx: dict[str, Any]):
        self.ctx = ctx or {}

    def is_running(self) -> bool:
        return bool(self.running and self.cutscene is not None)

    def start_cutscene(self, cutscene: Any, *, once: bool = True) -> bool:
        """Start a cutscene.

        Accepts:
          - raw dicts (script/video)
          - ScriptCutscene / VideoCutscene instances
        """

        if cutscene is None:
            return False

        # raw dict => infer type
        if isinstance(cutscene, dict):
            name = cutscene.get("name") or cutscene.get("id") or "<cutscene>"
            if cutscene.get("script"):
                cutscene = ScriptCutscene(name, cutscene)
            else:
                cutscene = VideoCutscene(name, cutscene)

        name = getattr(cutscene, "name", None)
        if once and name and name in self.completed:
            return False

        self.cutscene = cutscene
        self.running = True

        # lock player input (but keep Player.update() running for movement/animation)
        self._lock_player()

        if hasattr(self.cutscene, "start"):
            try:
                self.cutscene.start(self.ctx)
            except Exception:
                pass

        return True

    def _lock_player(self):
        player = self.ctx.get("player")
        if player is None:
            return

        self._player_prev = {
            "input_disabled": bool(getattr(player, "input_disabled", False)),
            "controlled": bool(getattr(player, "controlled", True)),
            "blocked": bool(getattr(player, "blocked", False)),
        }

        try:
            player.input_disabled = True
        except Exception:
            pass

        # keep Player.update() using cutscene-driven direction/speed
        try:
            player.controlled = True
        except Exception:
            pass

        try:
            player.blocked = False
        except Exception:
            pass

    def _unlock_player(self):
        player = self.ctx.get("player")
        if player is None:
            return

        try:
            player.input_disabled = self._player_prev.get("input_disabled", False)
        except Exception:
            pass

        try:
            player.controlled = self._player_prev.get("controlled", True)
        except Exception:
            pass

        try:
            player.blocked = self._player_prev.get("blocked", False)
        except Exception:
            pass

        try:
            player.direction.update(0, 0)
            player.is_running = False
        except Exception:
            pass

    def end_cutscene(self, *, mark_completed: bool = True):
        if self.cutscene and mark_completed:
            name = getattr(self.cutscene, "name", None)
            if name:
                self.completed.add(name)

        self._unlock_player()

        self.cutscene = None
        self.running = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if the event was consumed by the cutscene."""
        if not self.is_running():
            return False

        # ESC skips
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.end_cutscene(mark_completed=True)
            return True

        # SPACE/ENTER advances blocking 'say'
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            if hasattr(self.cutscene, "advance"):
                try:
                    self.cutscene.advance()
                    return True
                except Exception:
                    return False

        # controller A also advances if present
        if event.type == pygame.JOYBUTTONDOWN:
            # don't hard depend on settings constants here
            if hasattr(self.cutscene, "advance"):
                try:
                    self.cutscene.advance()
                    return True
                except Exception:
                    return False

        return False

    def update(self, dt: float):
        if not self.is_running():
            self.running = False
            return

        # keep window size current for video scaling
        if self.screen:
            sz = self.screen.get_size()
            if sz != self.window_size:
                self.window_size = sz

        try:
            self.cutscene.update(dt, self.ctx)
        except Exception:
            # fail safe: end cutscene instead of crashing the game loop
            self.end_cutscene(mark_completed=False)
            return

        if getattr(self.cutscene, "done", False):
            self.end_cutscene(mark_completed=True)

    def draw(self):
        if not (self.screen and self.is_running()):
            return

        # video overlays, etc.
        if hasattr(self.cutscene, "draw"):
            try:
                self.cutscene.draw(self.screen, self.window_size)
            except Exception:
                pass

        # subtitles (optional)
        sub = None
        if hasattr(self.cutscene, "get_subtitle"):
            try:
                sub = self.cutscene.get_subtitle()
            except Exception:
                sub = None

        if sub:
            self._draw_subtitle(sub)

    def _draw_subtitle(self, sub: Subtitle):
        game = self.ctx.get("game")
        font = None
        panel = None

        try:
            font = game.font.get("dialog") if game else None
        except Exception:
            font = None

        try:
            panel = game.ui_assets.dialog_panel if game else None
        except Exception:
            panel = None

        w, h = self.window_size
        if not font:
            font = pygame.font.Font(None, 28)

        label = f"{sub.who}: {sub.text}" if sub.who else sub.text
        text_surf = font.render(label, True, (255, 255, 255))

        if panel:
            x = (w - panel.get_width()) // 2
            y = h - panel.get_height() - 12
            self.screen.blit(panel, (x, y))
            self.screen.blit(text_surf, (x + 30, y + 22))
            return

        # fallback: simple rounded rect
        pad = 16
        box = pygame.Rect(40, h - 120, w - 80, 80)
        s = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 200), s.get_rect(), border_radius=14)
        pygame.draw.rect(s, (255, 255, 255, 160), s.get_rect(), width=2, border_radius=14)
        tx = pad
        ty = (box.height - text_surf.get_height()) // 2
        s.blit(text_surf, (tx, ty))
        self.screen.blit(s, box.topleft)
