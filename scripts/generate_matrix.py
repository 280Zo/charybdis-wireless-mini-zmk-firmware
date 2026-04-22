import json
from pathlib import Path

# === CONFIGURATION ===
board = "nice_nano"
dongle_board = "xiao_ble"

# automatically find all *.keymap filenames under ../config/keymap
keymap_dir = Path(__file__).parent.parent / "config" / "keymap"
keymaps = sorted(p.stem for p in keymap_dir.glob("*.keymap"))

# Map each format to the shields it should build
# All shields now live in charybdis directory
format_shields = {
    # Dongle mode: left+right as peripherals, dongle as central
    "dongle": ["charybdis_left", "charybdis_right", "charybdis_dongle"],
    "reset": ["settings_reset"],
}

# Map shields to their boards (most use nice_nano, dongle uses xiao)
shield_boards = {
    "charybdis_left": "nice_nano",
    "charybdis_right": "nice_nano",
    "charybdis_dongle": "xiao_ble",
    "settings_reset": "nice_nano",
}

groups = []
for keymap in keymaps:
    groups.append({
        "keymap": keymap,
        "format": "dongle",
        "name": f"{keymap}-dongle",
        "board": board,
    })

# Debug build: left half only, with USB logging enabled over CDC-ACM.
# Used for diagnosing BLE disconnect / sleep / hang issues on the left
# peripheral by tailing the left half over USB while it runs. See
# .github/workflows/build.yml for the -DCONFIG_ZMK_USB_LOGGING flags.
groups.append({
    "keymap": "qwerty",
    "format": "left_debug",
    "name": "qwerty-left-debug",
    "board": board,
})

# single reset entry
groups.append({
    "keymap": "default",
    "format": "reset",
    "name": "reset-nanov2",
    "board": board,
})

# Dump matrix as compact JSON (GitHub expects it this way)
print(json.dumps(groups))
