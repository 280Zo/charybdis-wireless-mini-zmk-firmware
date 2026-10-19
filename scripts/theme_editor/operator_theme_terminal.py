"""Keyboard selection and privacy-safe terminal presentation, stdlib only."""

from pathlib import Path
import os
import re
import select
import shutil
import sys
import termios
import textwrap
import tty

DESCRIPTIONS = {
    "bg": "Screen background (fixed black)",
    "label": "TOP WPM and KEY PRESS captions",
    "value": "TOP WPM and key-press numbers",
    "balance_track": "Key balance track",
    "balance_tick": "Key balance centre tick",
    "balance_marker": "Key balance moving marker",
    "mod_row_active": "Held modifiers below layer",
    "mod_row_inactive": "Unheld modifiers below layer",
    "caps": "Caps indicator",
    "brightness": "Brightness percentage",
    "wpm_peak": "WPM trailing peak marker",
    "battery_number": "Numbers inside battery boxes",
    "slot_active_text": "Active profile number",
    "slot_inactive_text": "Inactive profile numbers",
    "usb_icon": "USB power icon",
    "mod_active": "Held modifiers in legacy indicator",
    "mod_inactive": "Legacy unheld modifiers",
    "mod_separator": "Legacy modifier separators",
    "mod_caps_word": "Legacy Caps Word indicator",
    "wpm_bar_active": "Lit WPM history bars",
    "wpm_bar_inactive": "Unlit WPM history bars",
    "wpm_text": "Live WPM number",
    "layer_text": "Layer name",
    "layer_dot_active": "Active layer indicator",
    "layer_dot_inactive": "Inactive layer indicators",
    "battery_fill": "Normal battery arc and number box",
    "battery_ring": "Normal empty battery ring",
    "battery_bg": "Battery backing",
    "battery_label": "Battery caption",
    "battery_disconnected_fill": "Disconnected battery fill",
    "battery_disconnected_ring": "Disconnected empty ring",
    "battery_disconnected_label": "Disconnected battery caption",
    "battery_low_fill": "Low-battery arc and box",
    "battery_low_ring": "Low-battery empty ring",
    "usb_active_bg": "Selected USB button",
    "usb_inactive_bg": "Unselected USB button",
    "ble_active_bg": "Selected Bluetooth button",
    "ble_inactive_bg": "Unselected Bluetooth button",
    "output_active_text": "Selected output text",
    "output_inactive_text": "Unselected output text",
    "slot_active_bg": "Active profile box",
    "slot_inactive_bg": "Inactive profile boxes",
    "slot_text": "Profile captions",
    "texture": "Dots or hatch texture",
    "texture_faint": "Fine-grid texture",
}


def safe_text(value):
    return "".join(c if c.isprintable() else "?" for c in str(value))


def display_path(path: Path, roots: dict[str, Path]) -> str:
    for name, root in roots.items():
        try:
            relative = path.absolute().relative_to(root.absolute())
            return safe_text(
                str(relative) if name == "repo" else f"<{name}>/{relative}"
            )
        except ValueError:
            continue
    return "<external-file>"


def _palette_layout(palette, width=120, colour=False, selected=None):
    columns = 2 if width >= 100 else 1
    cell_width = max(16, (width - 3 * (columns - 1)) // columns)
    header = "   # Colour   Element".ljust(cell_width) + (
        " |    # Colour   Element" if columns == 2 else ""
    )
    blocks = []
    entries = list(palette["colors"].items())
    for start in range(0, len(entries), columns):
        cells = []
        for index in range(start, min(start + columns, len(entries))):
            role, color = entries[index]
            prefix = ("> " if index == selected else "  ") + f"{index + 1:02} "
            description = textwrap.wrap(DESCRIPTIONS[role], width=cell_width - 14) or [
                ""
            ]
            first = prefix + color.upper() + "  " + description[0]
            if colour:
                rgb = int(color[1:], 16)
                first = (
                    prefix
                    + f"\x1b[48;2;{rgb >> 16};{rgb >> 8 & 255};{rgb & 255}m{color.upper()}\x1b[0m  "
                    + description[0]
                )
            cells.append([first] + [" " * 14 + s for s in description[1:]])
        rows = []
        for line in range(max(map(len, cells))):
            pieces = []
            for cell in cells:
                value = cell[line] if line < len(cell) else ""
                visible = len(re.sub(r"\x1b\[[0-9;]*m", "", value))
                pieces.append(value + " " * max(0, cell_width - visible))
            rows.append(" | ".join(pieces).rstrip())
        blocks.append(rows)
    return header.rstrip()[:width], blocks, columns


def format_palette_table(palette, width=120, colour=False):
    header, blocks, _ = _palette_layout(palette, width, colour)
    return "\n".join([header] + [line for block in blocks for line in block]) + "\n\n"


def choose_palette_line(palette, prompt, output, width=120):
    roles = list(palette["colors"])
    while True:
        print(format_palette_table(palette, width, False), file=output)
        value = prompt("Colour number (p preview, s save, q back): ").strip().lower()
        if value == "s":
            return "save"
        if value == "p":
            return "preview"
        if value == "q":
            return None
        if value.isdigit() and 1 <= int(value) <= len(roles):
            role = roles[int(value) - 1]
            if role != "bg":
                return role
            print("The background is fixed black.", file=output)


def _palette_key(descriptor):
    char = os.read(descriptor, 1)
    if char == b"\x03":
        raise KeyboardInterrupt()
    if char in (b"q", b"\x04", b""):
        return "quit"
    if char in (b"s", b"S"):
        return "save"
    if char in (b"p", b"P"):
        return "preview"
    if char in (b"\r", b"\n"):
        return "enter"
    if char == b"\x1b":
        sequence = b""
        for _ in range(2):
            if not select.select([descriptor], [], [], 0.08)[0]:
                break
            sequence += os.read(descriptor, 1)
        return {
            b"[A": "up",
            b"OA": "up",
            b"[B": "down",
            b"OB": "down",
            b"[C": "right",
            b"OC": "right",
            b"[D": "left",
            b"OD": "left",
        }.get(sequence, "quit")
    return "other"


class Terminal:
    def choose_palette(self, palette, selected=None):
        if not self.stream.isatty() or not self.output.isatty():
            role = choose_palette_line(
                palette,
                self.prompt,
                self.output,
                shutil.get_terminal_size((120, 24)).columns,
            )
            if role in palette["colors"]:
                self.palette_selection = role
            return role
        descriptor = self.stream.fileno()
        previous = termios.tcgetattr(descriptor)
        roles = list(palette["colors"])
        if selected is None:
            selected = self.palette_selection
        selected = (
            roles.index(selected)
            if selected in roles and selected != "bg"
            else next(i for i, role in enumerate(roles) if role != "bg")
        )
        try:
            tty.setcbreak(descriptor)
            while True:
                self.palette_selection = roles[selected]
                size = shutil.get_terminal_size((120, 24))
                width = max(16, size.columns - 1)
                header, blocks, columns = _palette_layout(
                    palette, width, "NO_COLOR" not in os.environ, selected
                )
                budget = max(1, size.lines - 5)
                first = selected // columns
                used = min(len(blocks[first]), budget)
                while first > 0 and used + len(blocks[first - 1]) <= budget:
                    first -= 1
                    used += len(blocks[first])
                visible = []
                for block in blocks[first:]:
                    remaining = budget - len(visible)
                    if remaining <= 0:
                        break
                    visible += block[:remaining]
                frame = (
                    ["Choose a colour", header]
                    + visible
                    + ["Arrows/Enter; p preview; s save; q back"[:width]]
                )
                print("\n".join(frame), file=self.output, flush=True)
                key = _palette_key(descriptor)
                if key == "quit":
                    return None
                if key == "save":
                    return "save"
                if key == "preview":
                    return "preview"
                if key == "enter":
                    return roles[selected]
                delta = {"up": -columns, "down": columns, "left": -1, "right": 1}.get(
                    key, 0
                )
                if delta:
                    selected = (selected + delta) % len(roles)
                    while roles[selected] == "bg":
                        selected = (selected + delta) % len(roles)
                if "NO_COLOR" not in os.environ:
                    print(f"\x1b[{len(frame)}A\x1b[J", end="", file=self.output)
        finally:
            termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)

    def __init__(self, stream=None, output=None):
        self.stream = stream or sys.stdin
        self.output = output or sys.stdout
        self.palette_selection = None

    def prompt(self, label):
        print(label, end="", file=self.output, flush=True)
        value = self.stream.readline()
        if value == "":
            raise EOFError()
        return value.rstrip("\r\n")

    def choose(self, title, options):
        title = safe_text(title)
        options = [safe_text(o) for o in options]
        if not self.stream.isatty() or not self.output.isatty():
            while True:
                print(title, file=self.output)
                for i, option in enumerate(options, 1):
                    print(f" {i}. {option}", file=self.output)
                value = self.prompt("Select number (q = back/quit): ").strip().lower()
                if value == "q":
                    return None
                if value.isdigit() and 1 <= int(value) <= len(options):
                    return int(value) - 1
        descriptor = self.stream.fileno()
        previous = termios.tcgetattr(descriptor)
        selected = 0
        try:
            tty.setcbreak(descriptor)
            while True:
                size = shutil.get_terminal_size((80, 24))
                width = max(
                    1, size.columns - 1
                )  # Avoid right-margin automatic wrapping.
                height = max(1, size.lines - 1)
                clip = lambda line: (
                    line if len(line) <= width else line[: max(0, width - 1)] + "~"
                )
                if height < 3:
                    frame = [clip(" > " + options[selected])]
                else:
                    count = min(len(options), height - 2)
                    first = min(max(0, selected - count // 2), len(options) - count)
                    frame = [clip(title)]
                    frame += [
                        clip((" > " if i == selected else "   ") + options[i])
                        for i in range(first, first + count)
                    ]
                    frame.append(
                        clip(f"{selected + 1}/{len(options)}  ↑/↓ Enter; q = back/quit")
                    )
                print("\n".join(frame), file=self.output, flush=True)
                char = os.read(descriptor, 1)
                if char in (b"\r", b"\n"):
                    return selected
                if char in (b"q", b"\x04", b""):
                    return None
                if char == b"\x03":
                    raise KeyboardInterrupt()
                if char == b"\x1b":
                    sequence = b""
                    for _ in range(2):
                        if not select.select([descriptor], [], [], 0.08)[0]:
                            break
                        sequence += os.read(descriptor, 1)
                    if sequence in (b"[A", b"OA"):
                        selected = (selected - 1) % len(options)
                    elif sequence in (b"[B", b"OB"):
                        selected = (selected + 1) % len(options)
                    else:
                        return None
                if "NO_COLOR" not in os.environ:
                    print(f"\x1b[{len(frame)}A\x1b[J", end="", file=self.output)
        finally:
            termios.tcsetattr(descriptor, termios.TCSADRAIN, previous)
