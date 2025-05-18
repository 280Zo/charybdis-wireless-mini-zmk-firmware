import json

# === CONFIGURATION ===
board = "nice_nano_v2"

keymaps = ["qwerty", "colemak_dh", "graphite"]

# Map each format to the shields it should build
format_shields = {
    "bt": ["charybdis_left", "charybdis_right"],
    "dongle": ["charybdis_left", "charybdis_right", "charybdis_dongle"]
}

# === GENERATE INDIVIDUAL BUILD MATRIX ===
groups = []

for keymap in keymaps:
    for format_name, shields in format_shields.items():
        for shield in shields:
            groups.append({
                "name": f"firmware-charybdis-{keymap}-{format_name}-{shield}",
                "board": board,
                "keymap": keymap,
                "format": format_name,
                "shield": shield,
                "artifact-name": f"charybdis-{keymap}-{format_name}-{shield}"
            })

# Add a single reset build
groups.append({
    "name": "firmware-reset-nanov2",
    "board": board,
    "keymap": "default",
    "format": "reset",
    "shield": "settings_reset",
    "artifact-name": "reset-nanov2"
})

# Dump matrix as compact JSON (GitHub expects it this way)
print(json.dumps(groups))