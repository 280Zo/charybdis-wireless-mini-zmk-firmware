import json

# === CONFIGURATION ===
board = "nice_nano_v2"
keymaps = ["qwerty", "colemak_dh", "graphite"]

# Map each format to the shields it should build
format_shields = {
    "bt": ["charybdis_left", "charybdis_right"],
    "dongle": ["charybdis_left", "charybdis_right", "charybdis_dongle"],
    "reset": ["settings_reset"],
}

groups = []
for keymap in keymaps:
    for fmt in ["bt", "dongle"]:
        groups.append({
            "keymap": keymap,
            "format": fmt,
            "name": f"{keymap}-{fmt}"
        })

# single reset entry
groups.append({
    "keymap": "default",
    "format": "reset",
    "name": "reset-nanov2"
})

# Dump matrix as compact JSON (GitHub expects it this way)
print(json.dumps(groups))