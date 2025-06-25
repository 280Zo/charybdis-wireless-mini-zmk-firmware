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

# Add new layouts here, then update the maps below
# then and add the new keymap in the .github/workflows/build.yml

# Store maps
LAYOUT_MAPS = {
    'q2c': QWERTY_TO_COLEMAK_DH,
    'c2q': COLEMAK_DH_TO_QWERTY,
    'q2g': QWERTY_TO_GRAPHITE,
    'g2q': GRAPHITE_TO_QWERTY,
}

OUTPUT_FILE_NAMES = {
    'q2c': 'colemak_dh.keymap',
    'c2q': 'qwerty.keymap',
    'q2g': 'graphite.keymap',
    'g2q': 'qwerty.keymap',
}