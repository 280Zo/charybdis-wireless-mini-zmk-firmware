#!/usr/bin/env python3
"""Keyboard-driven Operator palette editor. Never commits, flashes or downloads."""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from uuid import uuid4

from theme_editor import operator_themes as themes
from theme_editor.operator_theme_preview import StaticRenderer
from theme_editor.operator_theme_terminal import display_path, safe_text


@dataclass(frozen=True)
class Paths:
    firmware: Path
    module: Path
    output: Path

    @property
    def library(self):
        return self.firmware / "config/dongle_prospector_operator_themes/themes.json"

    @property
    def registry(self):
        return self.library.with_name("operator_themes.generated.h")


def shown(path, paths):
    return display_path(
        path, {"repo": paths.firmware, "module": paths.module, "output": paths.output}
    )


def read_optional(path):
    return path.read_bytes() if path.exists() else None


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".theme-tweak-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_files(contents, originals, output):
    for path in contents:
        if path.is_symlink() or read_optional(path) != originals[path]:
            raise RuntimeError("An input changed or is a symlink; nothing overwritten.")
    backup = Path(tempfile.mkdtemp(prefix="theme-backup-", dir=output))
    for path, original in originals.items():
        (
            backup / (path.name + (".before" if original is not None else ".absent"))
        ).write_bytes(
            original
            if original is not None
            else b"File did not exist before this save.\n"
        )
    written = []
    try:
        for path, content in contents.items():
            if path.is_symlink() or read_optional(path) != originals[path]:
                raise RuntimeError("An input changed while saving.")
            written.append(path)
            atomic_write(path, content)
    except BaseException:
        for path in reversed(written):
            if not path.is_symlink() and read_optional(path) == contents[path]:
                if originals[path] is None:
                    path.unlink()
                else:
                    atomic_write(path, originals[path])
        raise
    print("Backup: <output>/" + backup.name)


def library_bytes(data):
    themes.validate_library(data)
    return (json.dumps(data, indent=2) + "\n").encode()


def configured_start(paths):
    matrix = paths.firmware / "build.yaml"
    if matrix.is_file():
        active = "\n".join(
            line
            for line in matrix.read_text().splitlines()
            if not line.lstrip().startswith("#")
        )
        starts = set(
            re.findall(r"dongle_prospector_operator_theme_(\w+)\.conf", active)
        )
        if len(starts) > 1 or starts - set(themes.BUILTIN_IDS):
            raise ValueError("Build matrix has ambiguous/legacy startup themes.")
        if starts:
            return starts.pop()
    return "default"


def contrast(a, b):
    def luminance(color):
        rgb = int(color[1:], 16)
        total = 0
        for shift, weight in ((16, 0.2126), (8, 0.7152), (0, 0.0722)):
            c = (rgb >> shift & 255) / 255
            total += weight * (
                c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            )
        return total

    lo, hi = sorted((luminance(a), luminance(b)))
    return (hi + 0.05) / (lo + 0.05)


def edit_color(palette, fields, color):
    colors = palette["colors"]
    for role in fields:
        colors[role] = color
    if set(fields) & {"layer_text", "battery_fill", "battery_low_fill"}:
        colors["battery_number"] = max(
            (colors["bg"], colors["layer_text"]),
            key=lambda c: min(
                contrast(c, colors["battery_fill"]),
                contrast(c, colors["battery_low_fill"]),
            ),
        )
    if set(fields) & {"layer_text", "slot_active_bg"}:
        colors["slot_active_text"] = max(
            (colors["bg"], colors["layer_text"]),
            key=lambda c: contrast(c, colors["slot_active_bg"]),
        )


def show_preview(palette, paths, renderer=None):
    print(
        "Generating preview… the first image may compile the local host harness.",
        flush=True,
    )
    owned = renderer is None
    renderer = renderer or StaticRenderer(paths)
    try:
        result, mode = renderer(palette, paths.output / ("theme-" + uuid4().hex[:8]))
        if not result.is_file() or result.stat().st_size == 0:
            raise RuntimeError("No preview image was generated.")
        result = result.resolve()
        print("Preview ready — " + mode)
        print("Open image: " + safe_text(str(result)))
        print("File link: " + result.as_uri())
        print("This is a static file; it remains available after the editor exits.")
        return result
    finally:
        if owned:
            renderer.close()


def run_build(paths):
    print(
        "Automatic build is blocked until the existing builder supports its safe prepared/offline, preserve-output handoff."
    )
    print("Saved themes/generated input are ready. No build was started.")
    print("Existing entry point: local-build/docker-compose.yml")
    print(
        "That builder must use a compatible module checkout, not merely the preview source."
    )
    return 2


def interactive(paths, ask=None, build=run_build, preview_renderer=None, terminal=None):
    from theme_editor.operator_theme_editor import interactive_impl

    return interactive_impl(
        paths, ask, build, sys.modules[__name__], terminal, preview_renderer
    )


@contextmanager
def session_lock(paths):
    paths.library.parent.mkdir(parents=True, exist_ok=True)
    with (paths.library.parent / ".theme-tweak.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another theme editor is using this library.") from None
        yield


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, default=root / "prospector-zmk-module")
    parser.add_argument("--output", type=Path, default=root / "scripts/theme-previews")
    args = parser.parse_args()
    paths = Paths(root, args.module.absolute(), args.output.absolute())
    try:
        themes.read_builtins(paths.module)
        if not paths.output.exists():
            if input(
                "Create preview/backup directory "
                + shown(paths.output, paths)
                + "? [y/N]: "
            ).strip().lower() not in ("y", "yes"):
                return 0
            paths.output.mkdir(parents=True)
        print("Palette source: " + shown(paths.module, paths))
        print("Black backgrounds and box styling stay fixed. No commits or flashing.")
        with session_lock(paths):
            renderer = StaticRenderer(paths)
            try:
                return interactive(paths, preview_renderer=renderer)
            finally:
                renderer.close()
    except (KeyboardInterrupt, EOFError):
        print("\nStopped. Confirmed saves/backups are kept; no firmware was flashed.")
        return 130
    except (ValueError, OSError, RuntimeError):
        print(
            "Editor could not continue safely. Check the selected module/input and output directory.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
