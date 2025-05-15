import json
import sys

# === CONFIGURATION ===
board = "nice_nano_v2"

keymaps = ["qwerty", "colemak_dh", "graphite"]

# Map each format to the shields it should build
format_shields = {
    "bt": ["charybdis_left", "charybdis_right"],
    "dongle": ["charybdis_left", "charybdis_right", "charybdis_dongle"]
}

reset_shields = ["settings_reset"]

# === GENERATE BUILD MATRIX ===
include = []

for keymap in keymaps:
    for format_name, shields in format_shields.items():
        for shield in shields:
            include.append({
                "board": board,
                "shield": shield,
                "keymap": keymap,
                "format": format_name
            })

        # Add settings_reset once per format per keymap
        include.append({
            "board": board,
            "shield": "settings_reset",
            "keymap": keymap,
            "format": format_name
        })

# === DEBUG ===
print(f"✅ Generated {len(include)} build combinations", file=sys.stderr)

# === OUTPUT TO STDOUT FOR GitHub Actions ===
print(json.dumps(include))