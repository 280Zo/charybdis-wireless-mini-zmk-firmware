# QWERTY → Colemak DH
QWERTY_TO_COLEMAK_DH = {
    'Q': 'Q', 'W': 'W', 'E': 'F', 'R': 'P', 'T': 'B', 'Y': 'J', 'U': 'L', 'I': 'U', 'O': 'Y', 'P': 'APOS',
    'A': 'A', 'S': 'R', 'D': 'S', 'F': 'T', 'G': 'G', 'H': 'M', 'J': 'N', 'K': 'E', 'L': 'I', 'SEMICOLON': 'O',
    'Z': 'Z', 'X': 'X', 'C': 'C', 'V': 'D', 'B': 'V', 'N': 'K', 'M': 'H',
}

# Colemak DH → QWERTY
COLEMAK_DH_TO_QWERTY = {v: k for k, v in QWERTY_TO_COLEMAK_DH.items()}

# QWERTY → Graphite
QWERTY_TO_GRAPHITE = {
    'Q': 'B', 'W': 'L', 'E': 'D', 'R': 'W', 'T': "Z", 'Y': "SQT", 'U': 'F', 'I': 'O', 'O': 'U', 'P': 'J',
    'A': 'N', 'S': 'R', 'D': 'T', 'F': 'S', 'G': 'G', 'H': 'Y', 'J': 'H', 'K': 'A', 'L': 'E', 'SEMICOLON': 'I',
    'Z': 'Q', 'X': 'X', 'C': 'M', 'V': 'C', 'B': 'V', 'N': 'K', 'M': 'P',
}

# Graphite → QWERTY
GRAPHITE_TO_QWERTY = {v: k for k, v in QWERTY_TO_GRAPHITE.items()}

# QWERTY → Canary
QWERTY_TO_CANARY = {
    'Q': 'W', 'W': 'L', 'E': 'Y', 'R': 'P', 'T': "B", 'Y': "Z", 'U': 'F', 'I': 'O', 'O': 'U', 'P': 'APOS',
    'A': 'C', 'S': 'R', 'D': 'S', 'F': 'T', 'G': 'G', 'H': 'M', 'J': 'N', 'K': 'E', 'L': 'I', 'SEMICOLON': 'A',
    'Z': 'Q', 'X': 'J', 'C': 'V', 'V': 'D', 'B': 'K', 'N': 'X', 'M': 'H',
}

# Canary → QWERTY
CANARY_TO_QWERTY = {v: k for k, v in QWERTY_TO_CANARY.items()}

# QWERTY → Focal
QWERTY_TO_FOCAL = {
    'Q': 'V', 'W': 'L', 'E': 'H', 'R': 'G', 'T': "K", 'Y': "Q", 'U': 'F', 'I': 'O', 'O': 'U', 'P': 'J',
    'A': 'S', 'S': 'R', 'D': 'N', 'F': 'T', 'G': 'B', 'H': 'Y', 'J': 'C', 'K': 'A', 'L': 'E', 'SEMICOLON': 'I',
    'Z': 'Z', 'X': 'X', 'C': 'M', 'V': 'D', 'B': 'P', 'N': 'APOS', 'M': 'W',
}

FOCAL_TO_QWERTY = {v: k for k, v in QWERTY_TO_FOCAL.items()}



# Add new layouts here, then update the maps below
# then and add the new keymap in the .github/workflows/build.yml

# Store maps
LAYOUT_MAPS = {
    'q2c': QWERTY_TO_COLEMAK_DH,
    'c2q': COLEMAK_DH_TO_QWERTY,
    'q2g': QWERTY_TO_GRAPHITE,
    'g2q': GRAPHITE_TO_QWERTY,
    'q2can': QWERTY_TO_CANARY,
    'can2q': CANARY_TO_QWERTY,
    'q2f': QWERTY_TO_FOCAL,
    'f2q': FOCAL_TO_QWERTY,
}

OUTPUT_FILE_NAMES = {
    'q2c': 'colemak_dh.keymap',
    'c2q': 'qwerty.keymap',
    'q2g': 'graphite.keymap',
    'g2q': 'qwerty.keymap',
    'q2can': 'canary.keymap',
    'can2q': 'qwerty.keymap',
    'q2f': 'focal.keymap',
    'f2q': 'qwerty.keymap',
}

# Run these commands to update all keymaps from the default qwerty
# python3 scripts/convert_keymap.py -c q2c --in-path config/keymap/qwerty.keymap
# python3 scripts/convert_keymap.py -c q2g --in-path config/keymap/qwerty.keymap
# python3 scripts/convert_keymap.py -c q2can --in-path config/keymap/qwerty.keymap
# python3 scripts/convert_keymap.py -c q2f --in-path config/keymap/qwerty.keymap