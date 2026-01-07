# ui_manager.py
from __future__ import annotations
import pygame
from typing import List, Optional

class UIManager:
    """
    Manages multiple overlays.
    - routes events top-down
    - updates/draws open overlays
    - exposes modal_open (blocks world input)
    """
    def __init__(self, overlays: List[object]):
        self.overlays = overlays
        self.modal_open = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        consumed = False

        # send events to top-most open overlays first
        for overlay in reversed(self.overlays):
            if getattr(overlay, "open", False):
                if hasattr(overlay, "handle_event"):
                    if overlay.handle_event(event) is True:
                        consumed = True
                        break

        # even if closed, some overlays can toggle open (ESC/START/TAB/SELECT)
        if not consumed:
            for overlay in reversed(self.overlays):
                if hasattr(overlay, "handle_event"):
                    if overlay.handle_event(event) is True:
                        consumed = True
                        break

        self.modal_open = any(getattr(o, "open", False) and getattr(o, "modal", True) for o in self.overlays)
        return consumed

    def update(self, dt: float, joystick: Optional[pygame.joystick.Joystick] = None):
        for overlay in self.overlays:
            if getattr(overlay, "open", False) and hasattr(overlay, "update"):
                overlay.update(dt, joystick=joystick)

        self.modal_open = any(getattr(o, "open", False) and getattr(o, "modal", True) for o in self.overlays)

    def draw(self, surface: pygame.Surface):
        # draw in original order (bottom -> top)
        for overlay in self.overlays:
            if getattr(overlay, "open", False) and hasattr(overlay, "draw"):
                overlay.draw(surface)
