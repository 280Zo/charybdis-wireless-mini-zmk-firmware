"""
Add a new layout mapping:
1. Create a dict for QWERTY->NEWLAYOUT
2. Create the reverse with {v: k for k, v in ...}
3. Add both to LAYOUT_MAPS as (src, dst): mapping
"""

# QWERTY -> Colemak DH
QWERTY_TO_COLEMAK_DH = {
    'Q': 'Q', 'W': 'W', 'E': 'F', 'R': 'P', 'T': 'B', 'Y': 'J', 'U': 'L', 'I': 'U', 'O': 'Y', 'P': 'APOS',
    'A': 'A', 'S': 'R', 'D': 'S', 'F': 'T', 'G': 'G', 'H': 'M', 'J': 'N', 'K': 'E', 'L': 'I', 'SEMICOLON': 'O',
    'Z': 'Z', 'X': 'X', 'C': 'C', 'V': 'D', 'B': 'V', 'N': 'K', 'M': 'H',
}

# Colemak DH -> QWERTY
COLEMAK_DH_TO_QWERTY = {v: k for k, v in QWERTY_TO_COLEMAK_DH.items()}

# QWERTY -> Graphite
QWERTY_TO_GRAPHITE = {
    'Q': 'B', 'W': 'L', 'E': 'D', 'R': 'W', 'T': "Z", 'Y': "SQT", 'U': 'F', 'I': 'O', 'O': 'U', 'P': 'J',
    'A': 'N', 'S': 'R', 'D': 'T', 'F': 'S', 'G': 'G', 'H': 'Y', 'J': 'H', 'K': 'A', 'L': 'E', 'SEMICOLON': 'I',
    'Z': 'Q', 'X': 'X', 'C': 'M', 'V': 'C', 'B': 'V', 'N': 'K', 'M': 'P',
}

# Graphite -> QWERTY
GRAPHITE_TO_QWERTY = {v: k for k, v in QWERTY_TO_GRAPHITE.items()}

# QWERTY -> Canary
QWERTY_TO_CANARY = {
    'Q': 'W', 'W': 'L', 'E': 'Y', 'R': 'P', 'T': "B", 'Y': "Z", 'U': 'F', 'I': 'O', 'O': 'U', 'P': 'APOS',
    'A': 'C', 'S': 'R', 'D': 'S', 'F': 'T', 'G': 'G', 'H': 'M', 'J': 'N', 'K': 'E', 'L': 'I', 'SEMICOLON': 'A',
    'Z': 'Q', 'X': 'J', 'C': 'V', 'V': 'D', 'B': 'K', 'N': 'X', 'M': 'H',
}

# Canary -> QWERTY
CANARY_TO_QWERTY = {v: k for k, v in QWERTY_TO_CANARY.items()}

# QWERTY -> Focal
QWERTY_TO_FOCAL = {
    'Q': 'V', 'W': 'L', 'E': 'H', 'R': 'G', 'T': "K", 'Y': "Q", 'U': 'F', 'I': 'O', 'O': 'U', 'P': 'J',
    'A': 'S', 'S': 'R', 'D': 'N', 'F': 'T', 'G': 'B', 'H': 'Y', 'J': 'C', 'K': 'A', 'L': 'E', 'SEMICOLON': 'I',
    'Z': 'Z', 'X': 'X', 'C': 'M', 'V': 'D', 'B': 'P', 'N': 'APOS', 'M': 'W',
}

FOCAL_TO_QWERTY = {v: k for k, v in QWERTY_TO_FOCAL.items()}

# Master dictionary keyed by (src, dst)
LAYOUT_MAPS = {
    # Colemak DH
    ("qwerty", "colemak_dh"): QWERTY_TO_COLEMAK_DH,
    ("colemakdh", "qwerty"): COLEMAK_DH_TO_QWERTY,

    # Graphite
    ("qwerty", "graphite"): QWERTY_TO_GRAPHITE,
    ("graphite", "qwerty"): GRAPHITE_TO_QWERTY,

    # Canary
    ("qwerty", "canary"): QWERTY_TO_CANARY,
    ("canary", "qwerty"): CANARY_TO_QWERTY,

    # Focal
    ("qwerty", "focal"): QWERTY_TO_FOCAL,
    ("focal", "qwerty"): FOCAL_TO_QWERTY,
}