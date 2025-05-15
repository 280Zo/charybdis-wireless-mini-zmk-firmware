import json

# === CONFIGURATION ===
board = "nice_nano_v2"

keymaps = ["qwerty", "colemak_dh", "graphite"]

# Map each format to the shields it should build
format_shields = {
    "bt": ["charybdis_left", "charybdis_right"],
    "dongle": ["charybdis_left", "charybdis_right", "charybdis_dongle"]
}

# === GENERATE GROUPED BUILD MATRIX ===
groups = []

for keymap in keymaps:
    for format_name, shields in format_shields.items():
        groups.append({
            "name": f"firmware-charybdis-{keymap}-{format_name}",
            "board": board,
            "keymap": keymap,
            "format": format_name,
            "shields": shields
        })

# Add a single reset build
groups.append({
    "name": "firmware-reset-nanov2",
    "board": board,
    "keymap": "default",
    "format": "reset",
    "shields": ["settings_reset"]
})

print(json.dumps(groups))
