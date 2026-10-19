import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_editor import operator_themes as themes
import test_operator_themes

SPEC = importlib.util.spec_from_file_location(
    "theme_tweak_public", Path(__file__).parents[1] / "theme-tweak.py"
)
ui = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ui
SPEC.loader.exec_module(ui)


class InteractiveTests(unittest.TestCase):
    def test_launcher_runs_from_another_cwd_with_only_grouped_helpers(self):
        scripts = self.paths.firmware / "scripts"
        scripts.mkdir()
        shutil.copyfile(ui.__file__, scripts / "theme-tweak.py")
        package = scripts / "theme_editor"
        package.mkdir()
        for source in (Path(ui.__file__).parent / "theme_editor").glob("*.py"):
            shutil.copyfile(source, package / source.name)
        result = subprocess.run(
            [sys.executable, "-B", str(scripts / "theme-tweak.py"), "--help"],
            cwd=self.paths.output,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--output", result.stdout)

    def test_default_preview_output_is_scripts_theme_previews(self):
        expected = self.paths.firmware / "scripts/theme-previews"
        expected.mkdir(parents=True)
        configured = []

        def make_renderer(paths):
            configured.append(paths.output)
            return mock.Mock()

        with (
            mock.patch.object(
                ui, "__file__", str(self.paths.firmware / "scripts/theme-tweak.py")
            ),
            mock.patch.object(
                sys, "argv", ["theme-tweak.py", "--module", str(self.paths.module)]
            ),
            mock.patch.object(sys, "stdin", io.StringIO("q\n")),
            redirect_stdout(io.StringIO()),
            mock.patch.object(ui, "StaticRenderer", side_effect=make_renderer),
        ):
            self.assertEqual(ui.main(), 0)
        self.assertEqual(configured, [expected])
        self.assertFalse((self.paths.firmware / "local-build").exists())

    def test_preview_prints_runtime_absolute_path_and_encoded_file_link(self):
        output_dir = self.paths.output / "previews with spaces #"
        output_dir.mkdir()
        paths = ui.Paths(self.paths.firmware, self.paths.module, output_dir)
        created = []

        def render(palette, output):
            image = output.with_suffix(".png")
            image.write_bytes(b"test renderer output")
            created.append(image.resolve())
            return image, "Test renderer"

        console = io.StringIO()
        with redirect_stdout(console):
            ui.show_preview(self.fixture.builtins["ember"], paths, render)
        self.assertIn("Open image: " + str(created[0]), console.getvalue())
        self.assertIn(created[0].as_uri(), console.getvalue())
        self.assertIn("%20", console.getvalue())
        self.assertIn("%23", console.getvalue())

    def test_preview_images_and_cache_are_ignored_but_source_is_not(self):
        root = Path(__file__).resolve().parents[2]
        if not (root / ".git").exists():
            self.skipTest("requires repository Git ignore rules")
        names = [
            "scripts/theme-previews/example.png",
            "scripts/theme-previews/renderer-cache/CMakeCache.txt",
            "scripts/theme_editor/operator_theme_preview.py",
        ]
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin"],
            input="\n".join(names) + "\n",
            text=True,
            capture_output=True,
            cwd=root,
        )
        self.assertEqual(result.stdout.splitlines(), names[:2])

    def test_cli_quits_without_starting_network_or_worker(self):
        with (
            mock.patch.object(
                ui, "__file__", str(self.paths.firmware / "scripts/theme-tweak.py")
            ),
            mock.patch.object(
                sys,
                "argv",
                [
                    "theme-tweak.py",
                    "--module",
                    str(self.paths.module),
                    "--output",
                    str(self.paths.output),
                ],
            ),
            mock.patch.object(sys, "stdin", io.StringIO("q\n")),
            redirect_stdout(io.StringIO()),
            mock.patch("socket.socket", side_effect=AssertionError("no server")),
            mock.patch(
                "threading.Thread.start", side_effect=AssertionError("no worker")
            ),
        ):
            self.assertEqual(ui.main(), 0)

    def setUp(self):
        self.fixture = test_operator_themes.LibraryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = ui.Paths(root, self.fixture.module, root)
        self.builds = []

    def run_ui(self, answers):
        answers = iter(answers)
        output = io.StringIO()
        with redirect_stdout(output):
            result = ui.interactive(
                self.paths,
                lambda _: next(answers),
                lambda paths: self.builds.append(paths) or 0,
            )
        return result, output.getvalue()

    def test_create_two_default_clones_and_restart(self):
        self.run_ui(
            [
                "7",
                "Copper",
                "1",
                "22",
                "#123456",
                "q",
                "4",
                "1",
                "6",
                "8",
                "Ocean",
                "4",
                "1",
                "6",
                "q",
            ]
        )
        data = themes.load_library(self.paths.library)
        self.assertEqual([p["name"] for p in data["custom"]], ["Copper", "Ocean"])
        self.assertEqual(data["custom"][0]["colors"]["wpm_text"], "#123456")
        self.assertEqual(data["custom"][1]["colors"]["wpm_text"], "#c2526a")
        _, output = self.run_ui(["q"])
        self.assertIn("Copper", output)
        self.assertIn("Ocean", output)
        self.assertFalse(self.paths.registry.exists())
        self.assertEqual(self.builds, [])

    def test_cancel_new_theme_after_preview_writes_no_library(self):
        self.run_ui(["7", "Ocean", "4", "2", "q", "2", "q"])
        self.assertFalse(self.paths.library.exists())
        self.assertFalse(self.paths.registry.exists())
        self.assertTrue(list(self.paths.output.glob("*.svg")))

    def test_existing_theme_edit_preserves_boxes_and_source(self):
        source = (self.paths.module / themes.PALETTE_REL).read_bytes()
        self.run_ui(["2", "1", "22", "abcdef", "q", "4", "1", "6", "q"])
        data = themes.load_library(self.paths.library)
        self.assertEqual(data["overrides"]["ember"]["wpm_text"], "#abcdef")
        self.assertEqual((self.paths.module / themes.PALETTE_REL).read_bytes(), source)
        self.assertIn('rx="4"', next(self.paths.output.glob("*.svg")).read_text())

    def test_final_checklist_shows_all_and_select_all(self):
        rc, output = self.run_ui(["1", "5", "1", "7", "9", "1"])
        self.assertEqual(rc, 0)
        for name in themes.BUILTIN_NAMES:
            self.assertIn("[x] " + name, output)
        self.assertIn("[ ] Default", output)
        self.assertEqual(len(self.builds), 1)
        header = self.paths.registry.read_text()
        for name in themes.BUILTIN_NAMES:
            self.assertIn(json.dumps(name), header)

    def test_custom_only_subset_keeps_other_saved_themes(self):
        data = themes.empty_library()
        data["custom"] = [
            themes.clone_default(self.fixture.builtins["default"], name)
            for name in ("Ocean", "Copper")
        ]
        self.paths.library.parent.mkdir(parents=True)
        self.paths.library.write_text(json.dumps(data))
        self.run_ui(["1", "5", "10", "7", "11", "1"])
        saved = themes.load_library(self.paths.library)
        self.assertEqual(len(saved["custom"]), 2)
        self.assertEqual(saved["selected"], [data["custom"][0]["id"]])
        self.assertNotIn('"Copper"', self.paths.registry.read_text())
        self.assertIn('"Ocean"', self.paths.registry.read_text())

    def test_cancel_selection_and_empty_selection_never_build(self):
        self.run_ui(["1", "5", "8", "9", "q", "6", "q"])
        self.assertEqual(self.builds, [])
        self.assertFalse(self.paths.registry.exists())
        self.run_ui(["1", "5", "9", "2", "6", "q"])
        self.assertEqual(self.builds, [])

    def test_stale_source_does_not_overwrite_user_work(self):
        self.paths.library.parent.mkdir(parents=True)
        self.paths.library.write_text(json.dumps(themes.empty_library()))
        old = self.paths.library.read_bytes()
        self.paths.library.write_text("user changed it")
        with self.assertRaises(RuntimeError):
            ui.save_files(
                {self.paths.library: b"ours"},
                {self.paths.library: old},
                self.paths.output,
            )
        self.assertEqual(self.paths.library.read_text(), "user changed it")

    def test_failed_second_write_rolls_back_both_inputs(self):
        self.paths.library.parent.mkdir(parents=True)
        self.paths.library.write_bytes(b"old json")
        self.paths.registry.write_bytes(b"old header")
        real = ui.atomic_write

        def fail_once(path, data):
            if path == self.paths.registry and data == b"new header":
                raise OSError("disk error")
            return real(path, data)

        with mock.patch.object(ui, "atomic_write", side_effect=fail_once):
            with self.assertRaises(OSError):
                ui.save_files(
                    {
                        self.paths.library: b"new json",
                        self.paths.registry: b"new header",
                    },
                    {
                        self.paths.library: b"old json",
                        self.paths.registry: b"old header",
                    },
                    self.paths.output,
                )
        self.assertEqual(self.paths.library.read_bytes(), b"old json")
        self.assertEqual(self.paths.registry.read_bytes(), b"old header")

    def test_build_gate_never_runs_legacy_destructive_builder(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("must not run")):
            self.assertNotEqual(ui.run_build(self.paths), 0)
        self.assertEqual(self.builds, [])

    def test_interruption_after_replace_restores_old_input(self):
        self.paths.library.parent.mkdir(parents=True)
        self.paths.library.write_bytes(b"old")
        real = ui.atomic_write

        def interrupt(path, content):
            real(path, content)
            if content == b"new":
                raise KeyboardInterrupt()

        with mock.patch.object(ui, "atomic_write", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                ui.save_files(
                    {self.paths.library: b"new"},
                    {self.paths.library: b"old"},
                    self.paths.output,
                )
        self.assertEqual(self.paths.library.read_bytes(), b"old")

    def test_changing_fills_recomputes_readable_text_and_keeps_metadata(self):
        palette = copy.deepcopy(self.fixture.builtins["ember"])
        palette["colors"]["layer_text"] = "#ffffff"
        palette["colors"]["slot_active_text"] = "#000000"
        ui.edit_color(palette, ("slot_active_bg",), "#111111")
        self.assertEqual(palette["colors"]["slot_active_text"], "#ffffff")
        self.assertEqual(palette["label_box_radius"], 4)

    def test_session_lock_covers_same_library_with_different_output_directory(self):
        other = ui.Paths(
            self.paths.firmware, self.paths.module, self.paths.output / "other"
        )
        with ui.session_lock(self.paths):
            with self.assertRaises(RuntimeError):
                with ui.session_lock(other):
                    self.fail("same library was opened by another editor")

    def test_external_edit_immediately_after_save_is_not_adopted_as_baseline(self):
        real = ui.save_files
        external_bytes = None

        def save_then_external_edit(contents, originals, output):
            nonlocal external_bytes
            real(contents, originals, output)
            if external_bytes is None:
                external = themes.load_library(self.paths.library)
                external["overrides"]["github"] = {"wpm_text": "#fedcba"}
                external_bytes = json.dumps(external).encode()
                self.paths.library.write_bytes(external_bytes)

        with mock.patch.object(ui, "save_files", side_effect=save_then_external_edit):
            with self.assertRaises(RuntimeError):
                self.run_ui(
                    [
                        "1",
                        "1",
                        "22",
                        "123456",
                        "q",
                        "4",
                        "1",
                        "6",
                        "2",
                        "1",
                        "22",
                        "abcdef",
                        "q",
                        "4",
                        "1",
                        "6",
                        "q",
                    ]
                )
        self.assertEqual(self.paths.library.read_bytes(), external_bytes)


if __name__ == "__main__":
    unittest.main()
