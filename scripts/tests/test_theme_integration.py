"""Optional real-module integration: set OPERATOR_THEME_TEST_MODULE explicitly."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import struct
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_editor import operator_themes as themes


@unittest.skipUnless(
    os.environ.get("OPERATOR_THEME_TEST_MODULE") and shutil.which("cc"),
    "Set OPERATOR_THEME_TEST_MODULE to run real-module compile checks",
)
class ModuleIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("OPERATOR_THEME_RENDER_LVGL"),
        "Set OPERATOR_THEME_RENDER_LVGL for local host screenshot checks",
    )
    def test_actual_host_pixels_cover_stats_wpm_layer_and_system_row(self):
        module = Path(os.environ["OPERATOR_THEME_TEST_MODULE"])
        builtins = themes.read_builtins(module)
        data = themes.empty_library()
        data["selected"] = ["ember"]
        data["overrides"] = {
            "ember": {
                "value": "#123456",
                "wpm_bar_active": "#edcba1",
                "layer_text": "#a1b2c3",
                "mod_row_active": "#abcdef",
            }
        }
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as directory:
            root = Path(directory)
            registry = root / "private.h"
            registry.write_text(themes.generate_registry(data, builtins, "ember"))
            image = root / "image.png"
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(module / "tools/render_operator_status.py"),
                    "--offline",
                    "--registry",
                    str(registry),
                    "--lvgl-dir",
                    os.environ["OPERATOR_THEME_RENDER_LVGL"],
                    "--cache-dir",
                    "/tmp/opencode",
                    "--scale",
                    "1",
                    "--output",
                    str(image),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            content = image.read_bytes()
            self.assertEqual(struct.unpack(">II", content[16:24]), (280, 240))
            chunks, offset = [], 8
            while offset < len(content):
                size = int.from_bytes(content[offset : offset + 4])
                if content[offset + 4 : offset + 8] == b"IDAT":
                    chunks.append(content[offset + 8 : offset + 8 + size])
                offset += size + 12
            raw = zlib.decompress(b"".join(chunks))
            rows = [raw[y * 841 + 1 : (y + 1) * 841] for y in range(240)]
            for color, start, end in (
                (b"\x12\x34\x56", 0, 35),
                (b"\xed\xcb\xa1", 40, 135),
                (b"\xa1\xb2\xc3", 95, 142),
                (b"\xab\xcd\xef", 150, 168),
            ):
                self.assertTrue(
                    any(color in row for row in rows[start:end]), (color, start, end)
                )

    def test_real_generated_subset_compiles_and_excluded_names_are_not_linked(self):
        module = Path(os.environ["OPERATOR_THEME_TEST_MODULE"])
        builtins = themes.read_builtins(module)
        self.assertEqual(builtins["default"]["colors"]["wpm_text"], "#c2526a")
        data = themes.empty_library()
        custom = themes.clone_default(builtins["default"], "Ocean")
        custom["colors"]["wpm_text"] = "#123456"
        data["custom"] = [custom]
        data["selected"] = ["ember", custom["id"]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "registry.h"
            registry.write_text(themes.generate_registry(data, builtins, "ember"))
            source = root / "test.c"
            source.write_text(
                '#include <assert.h>\n#include <string.h>\n#include "operator_theme.h"\n'
                "int main(void) { assert(operator_theme_count()==2);"
                'assert(strcmp(operator_theme_at(0)->name,"Ember")==0);'
                "assert(operator_theme_at(0)->label_box_radius==4);"
                "assert(operator_theme_at(0)->label_box_opacity==217);"
                "assert(operator_theme_at(1)->wpm_text==0x123456);"
                "assert(operator_theme_at(1)->layer_text==0xffffff); return 0;}"
            )
            op = module / themes.PALETTE_REL.parent
            binary = root / "verify"
            subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(op),
                    "-include",
                    str(registry),
                    str(source),
                    str(op / "operator_theme.c"),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            subprocess.run([str(binary)], check=True)
            linked = binary.read_bytes()
            self.assertNotIn(b"Synthwave\0", linked)
            self.assertNotIn(b"Glacier\0", linked)
            self.assertNotIn(b"GitHub\0", linked)


if __name__ == "__main__":
    unittest.main()
