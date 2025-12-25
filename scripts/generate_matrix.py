import json
from pathlib import Path

# === CONFIGURATION ===
boards = ["nice_nano_v2", "seeeduino_xiao_ble"]
# automatically find all *.keymap filenames under ../config/keymap
keymap_dir = Path(__file__).parent.parent / "config" / "keymap"
keymaps = sorted(p.stem for p in keymap_dir.glob("*.keymap"))

groups = []
for board in boards:
    for keymap in keymaps:
        for fmt in ["bt", "dongle"]:
            groups.append(
                {
                    "keymap": keymap,
                    "format": fmt,
                    "name": f"{keymap}-{fmt}",
                    "board": board,
                }
            )

    # single reset entry
    groups.append(
        {
            "keymap": "default",
            "format": "reset",
            "name": f"reset-{board}",
            "board": board,
        }
    )

# Dump matrix as compact JSON (GitHub expects it this way)
print(json.dumps(groups))
