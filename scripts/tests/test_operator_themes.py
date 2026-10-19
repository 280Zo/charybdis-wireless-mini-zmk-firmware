"""Portable creator tests: no ignored fixtures, Docker or dependency downloads."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_editor import operator_themes as themes


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.module = Path(self.temp.name)
        header = self.module / themes.PALETTE_REL
        header.parent.mkdir(parents=True)
        blocks = []
        for ident, name in zip(themes.BUILTIN_IDS, themes.BUILTIN_NAMES):
            colors = {role: "0xc2526a" for role in themes.COLOR_ROLES}
            colors["bg"] = "0x000000"
            if ident == "ember":
                colors["wpm_text"] = "0xff8800"
            lines = [
                f"#define OPERATOR_PALETTE_{ident.upper()} {{",
                f'.name = "{name}",',
                f".label_box_radius = {4 if ident == 'ember' else 0},",
                f".label_box_opacity = {217 if ident == 'ember' else 255},",
            ]
            lines += [f".{role} = {value}," for role, value in colors.items()]
            blocks.append((" " + chr(92) + "\n").join(lines + ["}"]) + "\n")
        header.write_text("".join(blocks))
        self.builtins = themes.read_builtins(self.module)
        self.data = themes.empty_library()

    def test_default_and_accepted_ember_are_extracted(self):
        self.assertEqual(self.builtins["default"]["colors"]["wpm_text"], "#c2526a")
        self.assertEqual(self.builtins["ember"]["colors"]["wpm_text"], "#ff8800")
        self.assertEqual(self.builtins["ember"]["label_box_radius"], 4)
        self.assertEqual(self.builtins["ember"]["label_box_opacity"], 217)

    def test_clone_is_complete_and_independent(self):
        first = themes.clone_default(self.builtins["default"], "Copper")
        second = themes.clone_default(self.builtins["default"], "Ocean")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["colors"], self.builtins["default"]["colors"])
        first["colors"]["wpm_text"] = "#abcdef"
        self.assertEqual(second["colors"]["wpm_text"], "#c2526a")

    def test_multiple_named_themes_and_custom_only(self):
        self.data["custom"] = [
            themes.clone_default(self.builtins["default"], n)
            for n in ("Copper", "Ocean")
        ]
        self.data["selected"] = [self.data["custom"][1]["id"]]
        generated = themes.generate_registry(self.data, self.builtins, "synthwave")
        self.assertIn('"Ocean"', generated)
        self.assertNotIn('"Copper"', generated)
        self.assertNotIn('"Synthwave"', generated)
        self.assertIn("OPERATOR_THEME_REGISTRY_START 0", generated)

    def test_select_all_and_deterministic_generation(self):
        self.data["selected"] = list(reversed(themes.BUILTIN_IDS))
        first = themes.generate_registry(self.data, self.builtins, "synthwave")
        self.data["selected"] = list(themes.BUILTIN_IDS)
        self.assertEqual(
            first, themes.generate_registry(self.data, self.builtins, "synthwave")
        )
        self.assertIn("OPERATOR_THEME_REGISTRY_START 3", first)

    def test_empty_unknown_duplicate_selection_rejected(self):
        for selected in ([], ["missing"], ["default", "default"]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                themes.generate_registry(
                    self.data | {"selected": selected}, self.builtins, "default"
                )

    def test_single_theme_and_builtin_override(self):
        self.data["selected"] = ["ember"]
        self.data["overrides"] = {"ember": {"wpm_text": "#123456"}}
        header = themes.generate_registry(self.data, self.builtins, "ember")
        self.assertIn(".wpm_text = 0x123456", header)
        self.assertIn(".label_box_radius = 4", header)
        self.assertNotIn('"Default"', header)

    def test_invalid_names_ids_colours_roles_versions(self):
        for name in ("", "a" * 25, "../bad", "bad\nname", 'bad"name', "🌊"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                themes.clone_default(self.builtins["default"], name)
        custom = themes.clone_default(self.builtins["default"], "Ocean")
        invalid = [
            self.data | {"version": 2},
            self.data | {"surprise": 1},
            self.data | {"custom": [custom, custom]},
            self.data | {"custom": [custom | {"id": "default"}]},
            self.data | {"custom": [custom | {"name": "Default"}]},
            self.data | {"overrides": {"ember": {"oops": "#123456"}}},
            self.data | {"overrides": {"ember": {"bg": "#111111"}}},
            self.data | {"overrides": {"ember": {"wpm_text": "#12345g"}}},
        ]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                themes.validate_library(data)

    def test_input_forms_and_invalid_hex(self):
        for value in ("#Ab12Ef", "0xAB12ef", "ab12ef"):
            self.assertEqual(themes.parse_color(value), "#ab12ef")
        for value in ("fff", "1234567", "-123456", "red", "123456;exit"):
            with self.assertRaises(ValueError):
                themes.parse_color(value)

    def test_read_palette_fails_closed_on_changed_format(self):
        source = (self.module / themes.PALETTE_REL).read_text()
        for changed in (
            source.replace(".wpm_text = 0xc2526a", ".wpm_text = SOME_MACRO", 1),
            source.replace(
                ".wpm_text = 0xc2526a,",
                ".wpm_text = 0xc2526a, .wpm_text = 0x123456,",
                1,
            ),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / themes.PALETTE_REL
                path.parent.mkdir(parents=True)
                path.write_text(changed)
                with self.assertRaises(ValueError):
                    themes.read_builtins(Path(tmp))

    def test_json_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "themes.json"
            path.write_text('{"version": 1, "version": 2}')
            with self.assertRaises(ValueError):
                themes.load_library(path)


if __name__ == "__main__":
    unittest.main()
