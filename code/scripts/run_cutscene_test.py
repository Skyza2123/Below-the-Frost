import sys
import time

# ensure project root in sys.path
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ensure `code/` directory is importable as top-level package for local modules
CODE_DIR = os.path.join(ROOT, 'code')
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from cutscenes.runner import ScriptCutscene
from cutscenes.registry import get_cutscene

class FakePos:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
    def update(self, x, y):
        self.x = float(x)
        self.y = float(y)

class FakeHitbox:
    def __init__(self, x, y):
        self.center = (int(x), int(y))

class FakePlayer:
    def __init__(self, x, y):
        self.pos = FakePos(x, y)
        self.hitbox = FakeHitbox(x, y)
        self.facing_direction = 'down'
        self.action = 'idle'
        self.frame_index = 0.0
    def block(self, duration=None):
        pass
    def unblock(self):
        pass
    def sync_rect_from_hitbox(self):
        pass


def run_test():
    data = get_cutscene('opening_raya_demo')
    cut = ScriptCutscene('opening_raya_demo', data)

    # create fake game context with player
    player = FakePlayer(-60, 320)
    ctx = {'game': None, 'player': player, 'character_sprites': []}

    cut.start(ctx)

    dt = 1.0 / 60.0
    t = 0.0
    last_print = 0.0
    print('Starting cutscene test...')
    while not cut.done and t < 10.0:
        cut.update(dt, ctx)
        t += dt
        # print every 0.2s
        if t - last_print >= 0.2:
            last_print = t
            print(f"t={t:.2f}s player.pos=({player.pos.x:.1f},{player.pos.y:.1f})")
        time.sleep(0.0)

    print('Cutscene done:', cut.done)
    print(f"Final player.pos=({player.pos.x:.1f},{player.pos.y:.1f})")

if __name__ == '__main__':
    run_test()
