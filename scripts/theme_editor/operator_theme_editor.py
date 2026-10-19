"""Pending-theme controller; terminal, renderer and persistence are injected."""

import copy
from pathlib import Path
import shutil
import sys
import os

from . import operator_themes as themes
from .operator_theme_terminal import (
    Terminal,
    DESCRIPTIONS,
    format_palette_table,
    choose_palette_line,
)


class PromptTerminal:
    """Line-mode adapter for callers that supply a prompt function."""

    def __init__(self, ask):
        self.prompt = ask

    def choose_palette(self, palette, selected=None):
        return choose_palette_line(palette, self.prompt, sys.stdout)

    def choose(self, title, options):
        while True:
            print(title)
            for i, option in enumerate(options, 1):
                print(f" {i}. {option}")
            answer = self.prompt("Select number (q = back/quit): ").strip().lower()
            if answer == "q":
                return None
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1


def interactive_impl(paths, ask, build, ui, terminal=None, preview_renderer=None):
    term = terminal or (PromptTerminal(ask) if ask is not None else Terminal())
    builtins = themes.read_builtins(paths.module)
    source = (paths.module / themes.PALETTE_REL).read_bytes()
    original_library = ui.read_optional(paths.library)
    original_registry = ui.read_optional(paths.registry)
    data = themes.load_library(paths.library)

    def diff(before, after):
        print("Pending colour changes:")
        for role, color in after["colors"].items():
            if color != before["colors"][role]:
                print(
                    f" {DESCRIPTIONS[role]}: {before['colors'][role].upper()} -> {color.upper()}"
                )

    def preview(draft):
        try:
            ui.show_preview(draft, paths, preview_renderer)
            return True
        except (OSError, RuntimeError):
            print(
                "Preview failed. Check compatible local renderer sources/dependencies and output permissions. No saved theme data was changed."
            )
            return False

    def confirm_save(draft):
        if not preview(draft):
            return False
        return term.choose("Save this theme?", ["Save", "Cancel"]) == 0

    def save(draft, is_new):
        nonlocal data, original_library
        if (paths.module / themes.PALETTE_REL).read_bytes() != source:
            raise RuntimeError(
                "Module palette changed; restart without overwriting it."
            )
        pending = copy.deepcopy(data)
        if is_new:
            pending["custom"].append(copy.deepcopy(draft))
            pending["selected"].append(draft["id"])
        elif draft["id"] in themes.BUILTIN_IDS:
            base = builtins[draft["id"]]["colors"]
            pending["overrides"][draft["id"]] = {
                r: c for r, c in draft["colors"].items() if c != base[r]
            }
        else:
            pending["custom"] = [
                copy.deepcopy(draft) if p["id"] == draft["id"] else p
                for p in pending["custom"]
            ]
        content = ui.library_bytes(pending)
        ui.save_files(
            {paths.library: content}, {paths.library: original_library}, paths.output
        )
        data, original_library = pending, content
        print(
            "Theme saved. Build input is unchanged until final selection confirmation."
        )

    while True:
        palettes = themes.resolved_palettes(data, builtins)
        selected = term.choose("Themes", [p["name"] for p in palettes] + ["New"])
        if selected is None:
            return 0
        is_new = selected == len(palettes)
        if is_new:
            try:
                draft = themes.clone_default(
                    builtins["default"], term.prompt("Theme name: ")
                )
                if draft["name"].casefold() in {p["name"].casefold() for p in palettes}:
                    raise ValueError("That name already exists.")
            except ValueError as error:
                print(str(error))
                continue
        else:
            draft = copy.deepcopy(palettes[selected])
        baseline = copy.deepcopy(draft)
        while True:
            print("\n" + draft["name"])
            print(
                format_palette_table(
                    draft,
                    shutil.get_terminal_size((120, 24)).columns,
                    sys.stdout.isatty() and "NO_COLOR" not in os.environ,
                )
            )
            action = term.choose(
                "Modify",
                ["Edit colour", "Import JSON", "Preview", "Save", "Build", "Back"],
            )
            dirty = is_new or draft != baseline
            if action is None or action in (4, 5):
                if dirty:
                    decision = term.choose(
                        "Unsaved changes", ["Save", "Discard", "Cancel"]
                    )
                    if decision in (None, 2):
                        continue
                    if decision == 0:
                        diff(baseline, draft)
                        if not confirm_save(draft):
                            continue
                        save(draft, is_new)
                        is_new = False
                        baseline = copy.deepcopy(draft)
                    else:
                        draft = copy.deepcopy(baseline)
                if action == 4:
                    # Same complete checklist/activation transaction as before.
                    current = themes.resolved_palettes(data, builtins)
                    included = set(data["selected"])
                    while True:
                        options = [
                            f"[{'x' if p['id'] in included else ' '}] {p['name']}"
                            for p in current
                        ]
                        choice = term.choose(
                            "Include in this build",
                            options + ["Select all", "Clear", "Done"],
                        )
                        if choice is None:
                            break
                        if choice < len(current):
                            included.symmetric_difference_update(
                                {current[choice]["id"]}
                            )
                        elif choice == len(current):
                            included = {p["id"] for p in current}
                        elif choice == len(current) + 1:
                            included.clear()
                        elif included:
                            pending = copy.deepcopy(data)
                            pending["selected"] = [
                                p["id"] for p in current if p["id"] in included
                            ]
                            start = ui.configured_start(paths)
                            chosen = [p for p in current if p["id"] in included]
                            startup = next(
                                (p for p in chosen if p["id"] == start), chosen[0]
                            )
                            print("Startup: " + startup["name"])
                            if (
                                term.choose(
                                    "Confirm selection and request build?",
                                    ["Confirm", "Cancel"],
                                )
                                != 0
                            ):
                                break
                            if (
                                paths.module / themes.PALETTE_REL
                            ).read_bytes() != source:
                                raise RuntimeError("Module palette changed; restart.")
                            ui.save_files(
                                {
                                    paths.library: ui.library_bytes(pending),
                                    paths.registry: themes.generate_registry(
                                        pending, builtins, start
                                    ).encode(),
                                },
                                {
                                    paths.library: original_library,
                                    paths.registry: original_registry,
                                },
                                paths.output,
                            )
                            return build(paths)
                        else:
                            print("Include at least one theme.")
                    continue
                if action is None:
                    return 0
                break
            if action == 0:
                while True:
                    role = term.choose_palette(draft)
                    if role is None:
                        break
                    if role == "preview":
                        preview(draft)
                        term.prompt("Press Enter to return to editing: ")
                        continue
                    if role == "save":
                        diff(baseline, draft)
                        if confirm_save(draft):
                            save(draft, is_new)
                            baseline = copy.deepcopy(draft)
                            is_new = False
                            break
                        continue
                    if role == "bg" or role not in draft["colors"]:
                        continue
                    print(DESCRIPTIONS[role] + ": " + draft["colors"][role].upper())
                    value = term.prompt("New colour (Enter cancels): ").strip()
                    if value:
                        try:
                            ui.edit_color(draft, (role,), themes.parse_color(value))
                        except ValueError as error:
                            print(str(error))
            elif action == 1:
                try:
                    value = term.prompt("JSON file (Enter cancels): ")
                    if not value:
                        continue
                    candidates = themes.import_candidates(
                        themes.read_import(Path(value)), builtins
                    )
                    choice = (
                        0
                        if len(candidates) == 1
                        else term.choose(
                            "Import theme", [p["name"] for p in candidates]
                        )
                    )
                    if choice is None:
                        continue
                    imported = themes.apply_import(draft, candidates[choice])
                    diff(draft, imported)
                    if (
                        term.choose(
                            "Apply imported colours to pending theme?",
                            ["Apply", "Cancel"],
                        )
                        == 0
                    ):
                        draft = imported
                except ValueError as error:
                    print(str(error))
            elif action == 2:
                preview(draft)
                term.prompt("Press Enter to return to editing: ")
            elif action == 3:
                diff(baseline, draft)
                if confirm_save(draft):
                    save(draft, is_new)
                    baseline = copy.deepcopy(draft)
                    is_new = False
