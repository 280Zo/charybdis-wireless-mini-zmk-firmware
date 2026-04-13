#!/usr/bin/env python3
"""
Generate keymap-drawer/stacked/stacked.yaml from keymap-drawer/stacked/qwerty.yaml.

Each key in the output carries legend slots from five source layers:

  Slot  Position    Layer   Color (see configs/config-stacked.yaml svg_extra_style)
  ----  ----------  ------  ------
   t    center      Base    neutral
   tl   top-left    Nav     blue
   tr   top-right   Num     green
   bl   bottom-left Xtra    purple
   br   bottom-right Sym    orange

Usage:
    python3 scripts/make_stacked.py

Regenerate whenever stacked.yaml changes (i.e. after `keymap parse`).
"""

import yaml
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent

# Layers to include and which slot each maps to (order matters for output dict)
SLOT_MAP = [
    ("Xtra", "tl"),
    ("Num",  "tr"),
    ("Nav",  "bl"),
    ("Sym",  "br"),
]


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def flatten(layer):
    return [key for row in layer for key in row]

def resolve(raw, raw_binding_map: dict) -> str:
    """
    Resolve a key value from qwerty.yaml to a plain display string.

    Handles:
    - Plain strings that may be raw ZMK binding refs (e.g. "&mm_f7")
    - Already-parsed dicts (e.g. {t: ▽, type: trans})
    - HRM keys: strips the hold/modifier symbol, returns only the tap letter
    - BT keys with both t+h fields: joins as "BT 0" etc.
    """
    if raw is None or raw == "":
        return ""

    if isinstance(raw, dict):
        key_type = raw.get("type", "")
        if key_type in ("trans", "ghost"):
            return ""
        t = str(raw.get("t", raw.get("tap", "")) or "")
        h = str(raw.get("h", raw.get("hold", "")) or "")
        # Home-row mods: show only the letter, not the modifier glyph
        if key_type == "hrm":
            return t
        # Keys with both a label and a sublabel (e.g. BT 0): join them
        if t and h:
            return f"{t} {h}"
        return t or h

    if isinstance(raw, str):
        if raw in raw_binding_map:
            return resolve(raw_binding_map[raw], raw_binding_map)
        return raw

    return str(raw)


def make_stacked_key(pos: int, layers: dict, raw_binding_map: dict):
    """
    Build a combined stacked key object for position `pos`.

    Returns a dict with populated slots, or a plain string when only the
    center (Base) slot has content.
    """
    def get(layer_name: str) -> str:
        layer = layers.get(layer_name, [])
        raw = layer[pos] if pos < len(layer) else ""
        return resolve(raw, raw_binding_map)

    center = get("Base")

    slots: dict = {}
    if center:
        slots["t"] = center

    for layer_name, slot in SLOT_MAP:
        val = get(layer_name)
        if val:
            slots[slot] = val

    if not slots:
        return ""
    if list(slots.keys()) == ["t"]:
        return slots["t"]
    return slots


def main() -> None:
    config  = load_yaml(SCRIPT_DIR / "keymap-drawer" / "configs" / "config-stacked.yaml")
    keymap  = load_yaml(SCRIPT_DIR / "keymap-drawer" / "stacked" / "qwerty.yaml")

    raw_binding_map: dict = (
        config.get("parse_config", {}).get("raw_binding_map", {})
    )
    layers: dict = keymap["layers"]
    layers_raw: dict = keymap["layers"]

    layers = {
        name: flatten(rows)
        for name, rows in layers_raw.items()
    }

    n_keys: int = len(layers["Base"])

    stacked = [make_stacked_key(i, layers, raw_binding_map) for i in range(n_keys)]

    out = {
        "layout": keymap["layout"],
        "layers": {"Stacked Keymap": stacked},
    }

    out_path = SCRIPT_DIR / "keymap-drawer" / "stacked" / "stacked.yaml"
    with open(out_path, "w") as f:
        yaml.dump(
            out,
            f,
            allow_unicode=True,
            default_flow_style=None,  # inline dicts, block lists/top-level
            sort_keys=False,
        )

    print(f"Written {out_path} ({n_keys} keys)")


if __name__ == "__main__":
    main()
