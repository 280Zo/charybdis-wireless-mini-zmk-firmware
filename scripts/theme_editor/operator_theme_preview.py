"""On-demand static Operator previews, with no server or background refresh.

Use the existing offline host renderer for production-widget PNGs. When local
render dependencies are absent, clearly label the dependency-free SVG fallback
as approximate, not a calibrated panel simulation. Never download dependencies.
"""

from html import escape
from pathlib import Path
import os
import shutil
import signal
import subprocess
import sys
from uuid import uuid4
from . import operator_themes as themes


def format_swatches(palette: dict, colour: bool = False) -> str:
    lines = [palette["name"] + " — colour palette"]
    for role, color in palette["colors"].items():
        swatch = ""
        if colour:
            rgb = int(color[1:], 16)
            swatch = f"\x1b[48;2;{rgb >> 16};{rgb >> 8 & 255};{rgb & 255}m  \x1b[0m "
        lines.append(f"{swatch}{role:28} {color.upper()}")
    return "\n".join(lines)


def render_mock(palette: dict, path: Path) -> Path:
    c = palette["colors"]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 240" width="560" height="480">',
        "<title>" + escape(palette["name"]) + " — approximate Operator mock</title>",
        '<g transform="scale(1.166666667 0.857142857)">',
        '<rect width="240" height="280" fill="#000000"/>',
    ]

    def rect(x, y, w, h, color, radius=0, opacity=1):
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{color}" fill-opacity="{opacity:.6f}"/>'
        )

    def text(x, y, value, role, size=12, anchor="start"):
        parts.append(
            f'<text x="{x}" y="{y}" font-family="monospace" font-size="{size}" text-anchor="{anchor}" fill="{c[role]}">{escape(str(value))}</text>'
        )

    text(120, 18, palette["name"], "layer_text", anchor="middle")
    for x, percent in ((44, 87), (196, 76)):
        parts.append(
            f'<circle cx="{x}" cy="49" r="20" fill="none" stroke="{c["battery_ring"]}" stroke-width="5"/>'
        )
        parts.append(
            f'<circle cx="{x}" cy="49" r="20" fill="none" stroke="{c["battery_fill"]}" stroke-width="5" stroke-dasharray="{percent * 1.256} 126" transform="rotate(-90 {x} 49)"/>'
        )
        rect(x - 15, 40, 30, 19, c["battery_fill"], 2)
        text(x, 54, percent, "battery_number", anchor="middle")
    text(120, 46, "USB", "output_active_text", anchor="middle")
    rect(91, 31, 58, 22, c["usb_active_bg"], 3)
    text(120, 46, "USB", "output_active_text", anchor="middle")
    for i in range(5):
        rect(
            78 + i * 18,
            67,
            13,
            16,
            c["slot_active_bg" if i == 0 else "slot_inactive_bg"],
            2,
        )
        text(
            84 + i * 18,
            79,
            i + 1,
            "slot_active_text" if i == 0 else "slot_inactive_text",
            10,
            "middle",
        )
    for i in range(24):
        height = 10 + (i * 11 % 34)
        rect(
            12 + i * 9,
            152 - height,
            6,
            height,
            c["wpm_bar_active" if i < 17 else "wpm_bar_inactive"],
        )
    rect(163, 100, 3, 48, c["wpm_peak"])
    radius = palette["label_box_radius"]
    opacity = palette["label_box_opacity"] / 255
    # Same metadata applied by production widgets, with opaque text over the box.
    rect(12, 156, 70, 30, c["wpm_bar_inactive"], radius, opacity)
    text(18, 177, "72", "wpm_text", 23)
    text(53, 176, "WPM", "label", 10)
    rect(123, 156, 105, 30, c["wpm_bar_inactive"], radius, opacity)
    text(175, 177, "BASE", "layer_text", 17, "middle")
    for i in range(5):
        parts.append(
            f'<circle cx="{149 + i * 13}" cy="194" r="3" fill="{c["layer_dot_active" if i == 0 else "layer_dot_inactive"]}"/>'
        )
    text(14, 214, "CTRL", "mod_row_active", 11)
    text(52, 214, "ALT SHIFT GUI", "mod_row_inactive", 11)
    text(218, 214, "80%", "brightness", 11, "end")
    rect(14, 225, 212, 4, c["balance_track"])
    rect(118, 222, 2, 10, c["balance_tick"])
    rect(139, 221, 4, 12, c["balance_marker"])
    text(14, 250, "TOP WPM", "label", 10)
    text(226, 250, "KEY PRESS", "label", 10, "end")
    text(14, 270, "96", "value", 18)
    text(226, 270, "12,345", "value", 18, "end")
    parts.append("</g></svg>")
    path.write_text("\n".join(parts) + "\n")
    return path.resolve()


def preview_palette(palette: dict, module_root: Path, output: Path) -> Path:
    # Do not invoke the host renderer's dependency preparation or ignored fixtures.
    return render_mock(palette, output)


class StaticRenderer:
    """Generate one static image on demand, with no server or background worker."""

    def __init__(self, paths):
        self.paths = paths
        self.cache = paths.output / ("renderer-" + uuid4().hex[:8])
        self.process = None
        self.closed = False

    def __call__(self, palette, output):
        if self.closed:
            raise RuntimeError("Preview renderer closed.")
        renderer = self.paths.module / "tools/render_operator_status.py"
        lvgl = self.paths.firmware / "modules/lib/gui/lvgl"
        if (
            not renderer.is_file()
            or not (lvgl / "lvgl.h").is_file()
            or not (lvgl / "CMakeLists.txt").is_file()
            or not shutil.which("cmake")
            or not shutil.which("cc")
        ):
            return render_mock(
                palette, output.with_suffix(".svg")
            ), "Approximate mock — real renderer unavailable"
        # Only sources explicitly chosen by the editor and the repository dependency
        # checkout are used. Never discover/execute an arbitrary cached binary.
        builtins = themes.read_builtins(self.paths.module)
        data = themes.empty_library()
        data["selected"] = [palette["id"]]
        if palette["id"] in themes.BUILTIN_IDS:
            builtins[palette["id"]] = palette
        else:
            data["custom"] = [palette]
        self.cache.mkdir(exist_ok=True)
        registry = self.cache / "pending.h"
        registry.write_text(themes.generate_registry(data, builtins, palette["id"]))
        target = output.with_suffix(".png")
        command = [
            sys.executable,
            "-B",
            str(renderer),
            "--offline",
            "--registry",
            str(registry),
            "--lvgl-dir",
            str(lvgl),
            "--cache-dir",
            str(self.cache),
            "--output",
            str(target),
            "--scale",
            "2",
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.process = process
        try:
            try:
                process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                self._terminate(process)
                raise RuntimeError("Host renderer timed out.") from None
            except BaseException:
                self._terminate(process)
                raise
            if process.returncode or not target.is_file():
                raise RuntimeError("Real renderer unavailable or failed.")
            return target, "LVGL production widgets"
        finally:
            self.process = None

    @staticmethod
    def _terminate(process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()

    def close(self):
        self.closed = True
        if self.process is not None:
            self._terminate(self.process)
            self.process = None
