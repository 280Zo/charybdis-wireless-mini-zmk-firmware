import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_editor import operator_themes as themes
import test_operator_themes


class ImportTests(unittest.TestCase):
    def setUp(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.builtins = fixture.builtins
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "theme.json"

    def test_import_single_palette_and_library(self):
        palette = themes.clone_default(self.builtins["default"], "Ocean")
        self.path.write_text(json.dumps(palette))
        self.assertEqual(
            themes.import_candidates(themes.read_import(self.path), self.builtins),
            [palette],
        )
        data = themes.empty_library()
        data["custom"].append(palette)
        self.path.write_text(json.dumps(data))
        self.assertEqual(
            len(themes.import_candidates(themes.read_import(self.path), self.builtins)),
            7,
        )

    def test_colours_only_apply_to_pending_draft(self):
        draft = copy.deepcopy(self.builtins["ember"])
        candidate = themes.clone_default(self.builtins["default"], "Ocean")
        candidate["colors"]["wpm_text"] = "#123456"
        applied = themes.apply_import(draft, candidate)
        self.assertEqual(applied["colors"]["wpm_text"], "#123456")
        for field in ("id", "name", "label_box_radius", "label_box_opacity"):
            self.assertEqual(applied[field], draft[field])
        self.assertEqual(draft["colors"]["wpm_text"], "#ff8800")

    def test_reject_duplicate_constants_depth_and_size(self):
        for text in (
            '{"x":1,"x":2}',
            '{"x":NaN}',
            '{"x":Infinity}',
            "[" * 17 + "0" + "]" * 17,
            " " * (1024 * 1024 + 1),
        ):
            self.path.write_text(text)
            with self.subTest(prefix=text[:30]), self.assertRaises(ValueError):
                themes.read_import(self.path)

    def test_reject_special_paths_without_opening_contents(self):
        self.path.write_text("{}")
        link = self.path.with_name("link.json")
        link.symlink_to(self.path)
        fifo = self.path.with_name("pipe.json")
        os.mkfifo(fifo)
        secret = self.path.with_name("credentials.json")
        secret.write_text("{}")
        directory_link = self.path.parent / "alias"
        directory_link.symlink_to(self.path.parent, target_is_directory=True)
        for path in (
            link,
            fifo,
            secret,
            self.path.parent,
            directory_link / "theme.json",
            Path("https://invalid/theme.json"),
        ):
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                themes.read_import(path)

    def test_malformed_types_and_collection_limits(self):
        palette = themes.clone_default(self.builtins["default"], "Ocean")
        for ident in ({}, [], 1, None):
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                themes.import_candidates(palette | {"id": ident}, self.builtins)
        data = themes.empty_library()
        for selected in ([{}], [None], ["default"] * 257):
            with self.assertRaises(ValueError):
                themes.validate_library(data | {"selected": selected})
        with self.assertRaises(ValueError):
            themes.validate_library(data | {"custom": [palette] * 257})


if __name__ == "__main__":
    unittest.main()
