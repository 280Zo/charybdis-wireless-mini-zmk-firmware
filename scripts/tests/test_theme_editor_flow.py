import copy
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

import test_theme_tweak
import test_operator_themes

ui = test_theme_tweak.ui
themes = test_theme_tweak.themes


class FlowTests(unittest.TestCase):
    def test_preview_inside_palette_uses_pending_edits_and_returns_to_editing(self):
        snapshots = []

        def render(palette, output):
            snapshots.append(copy.deepcopy(palette))
            image = output.with_suffix(".svg")
            image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            return image, "Test renderer"

        result, output = self.run_flow(
            ["2", "1", "22", "123456", "p", "", "20", "abcdef", "q", "q", "2"], render
        )
        self.assertEqual(result, 0)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["colors"]["wpm_text"], "#123456")
        self.assertEqual(output.count("Modify\n"), 2)
        self.assertFalse(self.paths.library.exists())
        self.assertFalse(self.paths.registry.exists())

    def test_cancelled_save_does_not_override_the_picker_cursor(self):
        from theme_editor import operator_theme_editor as editor

        answers = iter(["2", "1", "123456", "2", "q", "2"])
        owner = self

        class CursorTerminal(editor.PromptTerminal):
            calls = 0

            def choose_palette(self, palette, selected=None):
                self.calls += 1
                if self.calls == 1:
                    return "wpm_text"
                if self.calls == 2:
                    return "save"
                owner.assertIsNone(
                    selected, "controller must not reset the current highlight"
                )
                return None

        with redirect_stdout(io.StringIO()):
            ui.interactive(self.paths, terminal=CursorTerminal(lambda _: next(answers)))
        self.assertFalse(self.paths.library.exists())

    def test_editing_stays_in_palette_for_multiple_colours_until_save(self):
        _, output = self.run_flow(
            ["2", "1", "22", "123456", "20", "abcdef", "s", "1", "6", "q"]
        )
        saved = themes.load_library(self.paths.library)["overrides"]["ember"]
        self.assertEqual(saved["wpm_text"], "#123456")
        self.assertEqual(saved["wpm_bar_active"], "#abcdef")
        self.assertEqual(output.count("Modify\n"), 2)

    def test_cancelled_palette_save_returns_to_editing(self):
        self.run_flow(
            ["2", "1", "22", "123456", "s", "2", "20", "abcdef", "s", "1", "6", "q"]
        )
        saved = themes.load_library(self.paths.library)["overrides"]["ember"]
        self.assertEqual(saved["wpm_text"], "#123456")
        self.assertEqual(saved["wpm_bar_active"], "#abcdef")

    def test_leaving_palette_keeps_pending_edits_for_later_save(self):
        self.run_flow(["2", "1", "22", "123456", "q", "4", "1", "6", "q"])
        saved = themes.load_library(self.paths.library)["overrides"]["ember"]
        self.assertEqual(saved["wpm_text"], "#123456")

    def test_preview_generates_static_file_on_demand_without_server(self):
        calls = []

        def render(palette, output):
            calls.append(copy.deepcopy(palette))
            image = output.with_suffix(".png")
            image.write_bytes(b"fake renderer output")
            return image, "LVGL production widgets"

        result, output = self.run_flow(["1", "3", "", "q"], render)
        self.assertEqual(result, 0)
        self.assertIn("Generating preview", output)
        self.assertIn("Preview ready", output)
        self.assertIn(".png", output)
        self.assertNotIn("localhost", output)
        self.assertNotIn("http://", output)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "Default")
        self.assertEqual(len(list(self.paths.output.glob("*.png"))), 1)
        self.assertFalse(self.paths.library.exists())
        self.assertFalse(self.paths.registry.exists())

    def test_preview_keeps_result_visible_until_acknowledged(self):
        prompts = []
        answers = iter(["1", "3", "", "q"])

        def ask(label):
            prompts.append(label)
            return next(answers)

        with redirect_stdout(io.StringIO()):
            ui.interactive(self.paths, ask)
        self.assertTrue(any("Press Enter" in label for label in prompts))

    def test_edits_without_preview_do_not_run_renderer(self):
        def render(*args):
            self.fail("renderer must only run on request")

        self.run_flow(["2", "1", "22", "123456", "q", "q", "2"], render)

    def test_preview_failure_stays_in_editor_without_saving(self):
        def render(*args):
            raise RuntimeError("private diagnostics must not leak")

        result, output = self.run_flow(["2", "3", "", "q"], render)
        self.assertEqual(result, 0)
        self.assertIn("Preview failed", output)
        self.assertNotIn("private diagnostics", output)
        self.assertFalse(self.paths.library.exists())

    def test_palette_selection_changes_only_the_selected_table_role(self):
        self.run_flow(["2", "1", "22", "123456", "q", "4", "1", "6", "q"])
        saved = themes.load_library(self.paths.library)["overrides"]["ember"]
        self.assertEqual(saved["wpm_text"], "#123456")
        self.assertNotIn("wpm_bar_active", saved)

    def setUp(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = ui.Paths(root, fixture.module, root)
        self.builds = []

    def run_flow(self, answers, preview_renderer=None):
        answers = iter(answers)
        output = io.StringIO()
        with redirect_stdout(output):
            result = ui.interactive(
                self.paths,
                lambda _: next(answers),
                lambda paths: self.builds.append(paths) or 0,
                preview_renderer=preview_renderer,
            )
        return result, output.getvalue()

    def test_theme_list_new_not_build_or_clone_wording(self):
        _, output = self.run_flow(["q"])
        self.assertIn("New", output)
        self.assertNotIn("from Default", output)
        self.assertNotIn("Build", output)

    def test_q_from_clean_theme_quits_without_another_menu(self):
        result, output = self.run_flow(["1", "q"])
        self.assertEqual(result, 0)
        self.assertEqual(output.count("Themes\n"), 1)

    def test_new_theme_save_and_clean_quit(self):
        self.run_flow(["7", "Ocean", "1", "22", "123456", "q", "4", "1", "6", "q"])
        saved = themes.load_library(self.paths.library)["custom"][0]
        self.assertEqual(saved["name"], "Ocean")
        self.assertEqual(saved["colors"]["wpm_text"], "#123456")

    def test_dirty_quit_cancel_then_discard_leaves_no_save(self):
        self.run_flow(["1", "1", "22", "123456", "q", "q", "3", "q", "2", "q"])
        self.assertFalse(self.paths.library.exists())

    def test_build_is_in_theme_and_dirty_build_can_cancel(self):
        _, output = self.run_flow(
            ["1", "1", "22", "123456", "q", "5", "3", "q", "2", "q"]
        )
        self.assertIn("Build", output)
        self.assertEqual(self.builds, [])
        self.assertFalse(self.paths.registry.exists())

    def test_import_colours_reach_static_preview_and_confirmed_save(self):
        candidate = themes.clone_default(self.fixture.builtins["default"], "Imported")
        candidate["colors"]["wpm_text"] = "#abcdef"
        source = self.paths.output / "import.json"
        import json

        source.write_text(json.dumps(candidate))
        snapshots = []

        def render(palette, output):
            snapshots.append(copy.deepcopy(palette))
            result = output.with_suffix(".svg")
            result.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            return result, "Test renderer"

        self.run_flow(["2", "2", str(source), "1", "3", "", "4", "1", "6", "q"], render)
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[-1]["colors"]["wpm_text"], "#abcdef")
        self.assertEqual(snapshots[-1]["name"], "Ember")
        self.assertEqual(snapshots[-1]["label_box_radius"], 4)
        self.assertEqual(
            themes.load_library(self.paths.library)["overrides"]["ember"]["wpm_text"],
            "#abcdef",
        )


if __name__ == "__main__":
    unittest.main()
