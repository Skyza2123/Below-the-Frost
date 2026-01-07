# data_cutscenes.py

cutscenes = {
    "opening_raya_demo": {
        "ambience": None,
        "chapter": 0,
        "time_label": "Opening Demo",
        "narrator": "raya",
        "lock_player": True,
        "camera_follow": "raya",
        "script": [
            # (optional) place Raya at the spawn marker — main will strip this when auto-starting
            {"type": "set_pos", "character": "raya", "pos": (220, 320)},

            # walk forward a short distance (walk)
            {"type": "move_to", "character": "raya", "to": (220, 260), "run": False, "arrive_px": 4},
            {"type": "wait", "ms": 150},

            # run forward to show run animation
            {"type": "move_to", "character": "raya", "to": (220, 140), "run": True, "arrive_px": 4},
            {"type": "wait", "ms": 200},

            # pause and play idle animation
            {"type": "set_action", "character": "raya", "action": "idle", "ms": 400},

            # face all directions to exercise turn/face animations
            {"type": "face", "character": "raya", "dir": "right"},
            {"type": "wait", "ms": 150},
            {"type": "face", "character": "raya", "dir": "down"},
            {"type": "wait", "ms": 150},
            {"type": "face", "character": "raya", "dir": "left"},
            {"type": "wait", "ms": 150},
            {"type": "face", "character": "raya", "dir": "up"},
            {"type": "wait", "ms": 200},

            {"type": "end"},
        ],
    },
    "test_raya_enters_hospital": {
        "ambience": None,
        "chapter": 0,
        "time_label": "Hospital Entry",
        "narrator": "raya",
        "lock_player": True,
        "camera_follow": "raya",
        "script": [
            {"type": "face", "character": "raya", "dir": "down"},
            {"type": "wait", "ms": 300},
            {"type": "end"}
        ],
    }
}

