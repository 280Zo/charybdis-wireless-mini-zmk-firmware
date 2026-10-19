"""Portable Operator theme data and selected-registry generation (stdlib only)."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import stat
from uuid import UUID, uuid4

REPO = Path(__file__).resolve().parents[2]
BUILTIN_IDS = ("default", "ember", "glacier", "synthwave", "sea_shells", "github")
BUILTIN_NAMES = ("Default", "Ember", "Glacier", "Synthwave", "Sea Shells", "GitHub")
PALETTE_REL = Path(
    "boards/shields/prospector_adapter/src/layouts/operator/display_colors.h"
)
DEFAULT_MODULE = REPO / "prospector-zmk-module"
if not (DEFAULT_MODULE / PALETTE_REL).is_file():
    DEFAULT_MODULE = REPO.parent / "prospector-zmk-module"
COLOR_ROLES = tuple(
    """bg label value balance_track balance_tick balance_marker mod_row_active
mod_row_inactive caps brightness wpm_peak battery_number slot_active_text slot_inactive_text
usb_icon mod_active mod_inactive mod_separator mod_caps_word wpm_bar_active wpm_bar_inactive
wpm_text layer_text layer_dot_active layer_dot_inactive battery_fill battery_ring battery_bg
battery_label battery_disconnected_fill battery_disconnected_ring battery_disconnected_label
battery_low_fill battery_low_ring usb_active_bg usb_inactive_bg ble_active_bg ble_inactive_bg
output_active_text output_inactive_text slot_active_bg slot_inactive_bg slot_text texture texture_faint""".split()
)


def parse_color(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Colour must be six hex digits.")
    value = re.sub(r"^(#|0x)", "", value.strip(), flags=re.I)
    if not re.fullmatch(r"[a-fA-F0-9]{6}", value):
        raise ValueError("Use six hex digits, e.g. #FF8800, 0xFF8800 or FF8800.")
    return "#" + value.lower()


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z0-9 _-]{1,24}", name.strip()
    ):
        raise ValueError(
            "Name: 1–24 ASCII letters, digits, spaces, hyphens or underscores."
        )
    return name.strip()


def validate_palette(palette: dict) -> None:
    if not isinstance(palette, dict) or set(palette) != {
        "id",
        "name",
        "colors",
        "label_box_radius",
        "label_box_opacity",
    }:
        raise ValueError("Invalid palette fields.")
    ident = palette["id"]
    if not isinstance(ident, str) or len(ident) > 36:
        raise ValueError("Invalid palette identity.")
    if ident not in BUILTIN_IDS:
        try:
            if str(UUID(ident)) != ident:
                raise ValueError("Invalid identity.")
        except (ValueError, AttributeError) as error:
            raise ValueError("Invalid palette identity.") from error
    if validate_name(palette["name"]) != palette["name"]:
        raise ValueError("Trim the theme name.")
    colors = palette["colors"]
    if not isinstance(colors, dict) or set(colors) != set(COLOR_ROLES):
        raise ValueError("Palette requires every known colour role, without extras.")
    for value in colors.values():
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-f]{6}", value):
            raise ValueError("Stored colours must use lowercase #rrggbb.")
    if colors["bg"] != "#000000":
        raise ValueError("Background must remain true black.")
    for field, maximum in (("label_box_radius", 4), ("label_box_opacity", 255)):
        if type(palette[field]) is not int or not 0 <= palette[field] <= maximum:
            raise ValueError(f"Invalid {field}.")


def read_builtins(module_root: Path) -> dict:
    """Read literal palette macros only; never execute or rewrite source."""
    source = (module_root / PALETTE_REL).read_text()
    result = {}
    for ident, name in zip(BUILTIN_IDS, BUILTIN_NAMES):
        match = re.search(
            r"^#define OPERATOR_PALETTE_"
            + ident.upper()
            + r"\b(.*?)(?=^#define|^const struct|\Z)",
            source,
            re.M | re.S,
        )
        if not match:
            raise ValueError(f"Missing {name} palette.")
        block = match[1].replace("\\\n", "\n")
        pairs = re.findall(r"\.(\w+)\s*=\s*([^,]+),", block)
        fields = dict(pairs)
        if len(fields) != len(pairs) or set(fields) != set(COLOR_ROLES) | {
            "name",
            "label_box_radius",
            "label_box_opacity",
        }:
            raise ValueError(
                f"Changed/duplicate {name} palette fields; refusing to guess."
            )
        if fields.pop("name").strip() != json.dumps(name):
            raise ValueError("Unexpected builtin display name.")
        palette = {"id": ident, "name": name}
        for field in ("label_box_radius", "label_box_opacity"):
            if not re.fullmatch(r"[0-9]+", fields[field].strip()):
                raise ValueError("Expected literal box metadata.")
            palette[field] = int(fields.pop(field).strip())
        palette["colors"] = {}
        for field, literal in fields.items():
            literal = literal.strip()
            if not re.fullmatch(r"0x[0-9a-fA-F]{6}", literal):
                raise ValueError(f"Expected six-digit literal for {name}.{field}.")
            palette["colors"][field] = parse_color(literal)
        validate_palette(palette)
        result[ident] = palette
    return result


def empty_library() -> dict:
    return {"version": 1, "custom": [], "overrides": {}, "selected": list(BUILTIN_IDS)}


def clone_default(default: dict, name: str) -> dict:
    palette = copy.deepcopy(default)
    palette.update(id=str(uuid4()), name=validate_name(name))
    validate_palette(palette)
    return palette


def validate_library(data: dict) -> dict:
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "custom", "overrides", "selected"}
        or type(data["version"]) is not int
        or data["version"] != 1
    ):
        raise ValueError("Unknown theme library schema/version.")
    if (
        not isinstance(data["custom"], list)
        or not isinstance(data["overrides"], dict)
        or not isinstance(data["selected"], list)
    ):
        raise ValueError("Invalid library collections.")
    if len(data["custom"]) > 256 or len(data["selected"]) > 256:
        raise ValueError("Theme collection limit exceeded (256).")
    ids, names = set(BUILTIN_IDS), {n.casefold() for n in BUILTIN_NAMES}
    for palette in data["custom"]:
        validate_palette(palette)
        ident = palette["id"]
        try:
            if str(UUID(ident)) != ident:
                raise ValueError("Noncanonical UUID")
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError("Custom theme requires a canonical UUID.") from error
        if ident in ids or palette["name"].casefold() in names:
            raise ValueError("Duplicate theme ID or name.")
        ids.add(ident)
        names.add(palette["name"].casefold())
    for ident, changes in data["overrides"].items():
        if ident not in BUILTIN_IDS or not isinstance(changes, dict):
            raise ValueError("Unknown builtin override.")
        for role, color in changes.items():
            if (
                role not in COLOR_ROLES
                or parse_color(color) != color
                or (role == "bg" and color != "#000000")
            ):
                raise ValueError("Invalid colour override.")
    selected = data["selected"]
    if (
        not selected
        or any(not isinstance(i, str) or i not in ids for i in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("Select at least one known theme, without duplicates.")
    return data


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def load_library(path: Path) -> dict:
    if not path.exists():
        return empty_library()
    return validate_library(read_import(path))


def read_import(path: Path) -> dict:
    """Open an explicitly chosen regular JSON file without following symlinks."""
    raw_path = str(path)
    secret = re.compile(
        r"^(?:\.env(?:\..*)?|credentials.*|id_rsa.*|\.npmrc|\.netrc)$|\.(?:pem|key|tfstate|kdbx|cred)$",
        re.I,
    )
    if (
        "://" in raw_path
        or any(ord(c) < 32 or ord(c) == 127 for c in raw_path)
        or secret.search(path.name)
    ):
        raise ValueError("Unsupported or sensitive import path.")
    absolute = path.absolute()
    directory = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    descriptor = None
    try:
        for part in absolute.parts[1:-1]:
            next_directory = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            os.close(directory)
            directory = next_directory
        descriptor = os.open(
            absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1024 * 1024:
            raise ValueError("Import must be a regular JSON file of at most 1 MiB.")
        content = bytearray()
        while len(content) <= 1024 * 1024:
            chunk = os.read(descriptor, min(65536, 1024 * 1024 + 1 - len(content)))
            if not chunk:
                break
            content.extend(chunk)
        if len(content) > 1024 * 1024:
            raise ValueError("Import exceeds 1 MiB.")
        text = content.decode("utf-8")
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == chr(92):
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > 16:
                    raise ValueError("JSON nesting exceeds 16 levels.")
            elif char in "]}":
                depth -= 1

        def reject_constant(_):
            raise ValueError("Nonstandard JSON number.")

        return json.loads(
            text, object_pairs_hook=_unique_pairs, parse_constant=reject_constant
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("Cannot read a safe, valid JSON import.") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def import_candidates(data: dict, builtins: dict) -> list[dict]:
    if isinstance(data, dict) and "version" in data:
        return resolved_palettes(validate_library(data), builtins)
    validate_palette(data)
    return [copy.deepcopy(data)]


def apply_import(draft: dict, candidate: dict) -> dict:
    validate_palette(candidate)
    pending = copy.deepcopy(draft)
    pending["colors"] = copy.deepcopy(candidate["colors"])
    validate_palette(pending)
    return pending


def resolved_palettes(data: dict, builtins: dict) -> list[dict]:
    validate_library(data)
    palettes = copy.deepcopy(list(builtins.values()))
    for palette in palettes:
        palette["colors"].update(data["overrides"].get(palette["id"], {}))
    return palettes + copy.deepcopy(data["custom"])


def generate_registry(data: dict, builtins: dict, start_id: str) -> str:
    palettes = [
        p for p in resolved_palettes(data, builtins) if p["id"] in data["selected"]
    ]
    start = next((i for i, p in enumerate(palettes) if p["id"] == start_id), 0)
    lines = [
        "/* Generated by scripts/theme-tweak.py; do not edit by hand. */",
        "#pragma once",
        "#define OPERATOR_THEME_REGISTRY_VERSION 1",
        f"#define OPERATOR_THEME_REGISTRY_START {start}",
        "#define OPERATOR_THEME_REGISTRY_ENTRIES \\",
    ]
    for palette in palettes:
        validate_palette(palette)
        lines.append("    { .id = " + json.dumps(palette["id"]) + ", .palette = { \\")
        lines.append("        .name = " + json.dumps(palette["name"]) + ", \\")
        for field in ("label_box_radius", "label_box_opacity"):
            lines.append(f"        .{field} = {palette[field]}, \\")
        for role in COLOR_ROLES:
            lines.append(f"        .{role} = 0x{palette['colors'][role][1:]}, \\")
        lines.append("    } }, \\")
    return "\n".join(lines) + "\n\n"
