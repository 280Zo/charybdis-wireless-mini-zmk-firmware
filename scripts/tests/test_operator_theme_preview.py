import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_editor import operator_theme_preview as preview
import test_operator_themes


class PreviewTests(unittest.TestCase):
    def setUp(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.palette = copy.deepcopy(fixture.builtins["ember"])
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "preview.svg"

    def test_pending_palette_and_box_metadata_reach_mock(self):
        self.palette["colors"]["wpm_text"] = "#123456"
        before = copy.deepcopy(self.palette)
        result = preview.render_mock(self.palette, self.path)
        self.assertEqual(result, self.path.resolve())
        source = result.read_text()
        root = ET.fromstring(source)
        self.assertEqual(root.attrib["viewBox"], "0 0 280 240")
        self.assertIn("#123456", source)
        self.assertIn('rx="4"', source)
        self.assertIn('fill-opacity="0.850980"', source)
        self.assertIn('fill="#000000"', source)
        self.assertEqual(self.palette, before)

    def test_plain_swatches_are_readable_without_escape_codes(self):
        output = preview.format_swatches(self.palette, colour=False)
        self.assertIn("wpm_text", output)
        self.assertIn("#FF8800", output)
        self.assertNotIn("\x1b", output)
        self.assertIn("\x1b[48;2;", preview.format_swatches(self.palette, colour=True))

    def test_names_are_xml_escaped_even_outside_ui(self):
        self.palette["name"] = '<unsafe & "name">'
        preview.render_mock(self.palette, self.path)
        root = ET.parse(self.path).getroot()
        self.assertIn('<unsafe & "name">', "".join(root.itertext()))

    def test_no_host_renderer_or_dependencies_still_produces_preview(self):
        result = preview.preview_palette(self.palette, Path(self.temp.name), self.path)
        self.assertTrue(result.is_file())
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.path])

    def test_static_renderer_close_terminates_an_active_process(self):
        from types import SimpleNamespace

        paths = SimpleNamespace(
            firmware=Path(self.temp.name),
            module=Path(self.temp.name),
            output=Path(self.temp.name),
        )
        renderer = preview.StaticRenderer(paths)
        process = mock.Mock(pid=123, returncode=None)
        renderer.process = process
        with mock.patch.object(preview.os, "killpg"):
            renderer.close()
        self.assertTrue(renderer.closed)
        process.communicate.assert_called_once_with(timeout=2)

    def test_static_renderer_labels_dependency_free_fallback(self):
        from types import SimpleNamespace

        paths = SimpleNamespace(
            firmware=Path(self.temp.name),
            module=Path(self.temp.name),
            output=Path(self.temp.name),
        )
        renderer = preview.StaticRenderer(paths)
        result, mode = renderer(self.palette, self.path.with_suffix(""))
        self.assertEqual(result.suffix, ".svg")
        self.assertIn("Approximate", mode)
        self.assertIn("unavailable", mode)
        renderer.close()


if __name__ == "__main__":
    unittest.main()
