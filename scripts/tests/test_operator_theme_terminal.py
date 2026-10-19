import io
import os
from pathlib import Path
import pty
import sys
import termios
import threading
import time
import unittest
import re
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_editor import operator_theme_terminal as terminal
import test_operator_themes


class TerminalTests(unittest.TestCase):
    def test_palette_preview_hotkey_in_line_and_keyboard_modes(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        term = terminal.Terminal(io.StringIO("p\n"), io.StringIO())
        self.assertEqual(term.choose_palette(fixture.builtins["ember"]), "preview")
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        os.write(write_fd, b"P")
        self.assertEqual(terminal._palette_key(read_fd), "preview")

    def test_palette_remembers_colour_and_supports_keyboard_save(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        master, slave = pty.openpty()
        stream = os.fdopen(os.dup(slave), "r")
        self.addCleanup(stream.close)
        self.addCleanup(os.close, slave)
        self.addCleanup(os.close, master)

        class Output(io.StringIO):
            def isatty(self):
                return True

        before = termios.tcgetattr(slave)
        term = terminal.Terminal(stream, Output())
        for key, expected, initial in (
            (b"\r", "wpm_text", "wpm_text"),
            (b"s", "save", "wpm_text"),
            (b"\x1b[Cs", "save", "wpm_text"),
            (b"\r", "layer_text", None),
            (b"p", "preview", None),
            (b"\r", "layer_text", None),
        ):
            result = []
            thread = threading.Thread(
                target=lambda: result.append(
                    term.choose_palette(fixture.builtins["ember"], selected=initial)
                )
            )
            thread.start()
            for _ in range(100):
                if not termios.tcgetattr(slave)[3] & termios.ICANON:
                    break
                time.sleep(0.005)
            os.write(master, key)
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result, [expected])
            self.assertEqual(termios.tcgetattr(slave), before)

    def test_palette_line_mode_has_explicit_save_action(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        term = terminal.Terminal(io.StringIO("s\n"), io.StringIO())
        self.assertEqual(term.choose_palette(fixture.builtins["ember"]), "save")

    def test_two_column_palette_arrow_navigation_and_viewport(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        master, slave = pty.openpty()
        stream = os.fdopen(os.dup(slave), "r")
        self.addCleanup(stream.close)
        self.addCleanup(os.close, slave)
        self.addCleanup(os.close, master)

        class Output(io.StringIO):
            def isatty(self):
                return True

        output, result = Output(), []
        before = termios.tcgetattr(slave)
        with (
            mock.patch.object(
                terminal.shutil,
                "get_terminal_size",
                return_value=os.terminal_size((120, 10)),
            ),
            mock.patch.dict(os.environ, {"NO_COLOR": "1"}),
        ):
            thread = threading.Thread(
                target=lambda: result.append(
                    terminal.Terminal(stream, output).choose_palette(
                        fixture.builtins["ember"]
                    )
                )
            )
            thread.start()
            for _ in range(100):
                if not termios.tcgetattr(slave)[3] & termios.ICANON:
                    break
                time.sleep(0.005)
            os.write(master, b"\x1b[C\x1b[B\r")
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, ["balance_tick"])
        self.assertEqual(termios.tcgetattr(slave), before)
        self.assertIn(" | ", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())
        for frame in output.getvalue().split("Choose a colour\n")[1:]:
            self.assertLessEqual(len(frame.splitlines()), 8)
            self.assertTrue(all(len(line) <= 119 for line in frame.splitlines()))

    def test_palette_picker_reuses_table_and_fixed_background_cannot_be_edited(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        palette = fixture.builtins["ember"]
        output = io.StringIO()
        term = terminal.Terminal(io.StringIO("1\n22\n"), output)
        self.assertEqual(term.choose_palette(palette), "wpm_text")
        self.assertIn("Colour", output.getvalue())
        self.assertIn("Lit WPM history bars", output.getvalue())
        self.assertIn("Live WPM number", output.getvalue())
        self.assertIn("#FF8800", output.getvalue())
        self.assertIn("fixed", output.getvalue())

    def test_long_menu_scrolls_within_terminal_height_and_clips_labels(self):
        master, slave = pty.openpty()
        stream = os.fdopen(os.dup(slave), "r")
        self.addCleanup(stream.close)
        self.addCleanup(os.close, slave)
        self.addCleanup(os.close, master)

        class Output(io.StringIO):
            def isatty(self):
                return True

        output = Output()
        result = []
        before = termios.tcgetattr(slave)
        with mock.patch.object(
            terminal.shutil, "get_terminal_size", return_value=os.terminal_size((40, 8))
        ):
            thread = threading.Thread(
                target=lambda: result.append(
                    terminal.Terminal(stream, output).choose(
                        "Colour", ["Long description " * 8 + str(i) for i in range(50)]
                    )
                )
            )
            thread.start()
            for _ in range(100):
                if not termios.tcgetattr(slave)[3] & termios.ICANON:
                    break
                time.sleep(0.005)
            os.write(master, b"\x1b[B" * 10 + b"\r")
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [10])
        self.assertEqual(termios.tcgetattr(slave), before)
        frames = re.split(r"\x1b\[\d+A\x1b\[J", output.getvalue())
        for frame in frames:
            lines = frame.splitlines()
            self.assertLessEqual(len(lines), 7)
            self.assertTrue(all(len(line) <= 39 for line in lines))
            self.assertEqual(sum(line.startswith(" > ") for line in lines), 1)

    def test_paths_and_controls_are_neutral(self):
        root = Path("/synthetic/workspace")
        self.assertEqual(
            terminal.display_path(root / "config/a.json", {"repo": root}),
            "config/a.json",
        )
        self.assertEqual(
            terminal.display_path(
                Path("/synthetic/module/a.c"), {"module": Path("/synthetic/module")}
            ),
            "<module>/a.c",
        )
        self.assertEqual(
            terminal.display_path(Path("/outside/private/a.json"), {"repo": root}),
            "<external-file>",
        )
        self.assertNotIn("\x1b", terminal.safe_text("bad\x1b[31m\nname"))

    def test_palette_table_has_pairs_and_element_descriptions(self):
        fixture = test_operator_themes.LibraryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        palette = fixture.builtins["ember"]
        table = terminal.format_palette_table(palette, width=130, colour=False)
        self.assertIn("Colour", table)
        self.assertIn("WPM", table)
        self.assertTrue(any(line.count("#") == 2 for line in table.splitlines()))
        self.assertTrue(all(len(line) <= 130 for line in table.splitlines()))
        narrow = terminal.format_palette_table(palette, width=65, colour=False)
        self.assertFalse(any(line.count("#") > 1 for line in narrow.splitlines()))
        self.assertNotIn("\x1b", narrow)

    def test_line_fallback_and_quit(self):
        term = terminal.Terminal(io.StringIO("2\nq\n"), io.StringIO())
        self.assertEqual(term.choose("Themes", ["Default", "New"]), 1)
        self.assertIsNone(term.choose("Themes", ["Default", "New"]))

    def test_redirected_output_uses_line_mode_even_with_tty_input(self):
        class Input(io.StringIO):
            def isatty(self):
                return True

        output = io.StringIO()
        term = terminal.Terminal(Input("2\n"), output)
        self.assertEqual(term.choose("Themes", ["Default", "New"]), 1)
        self.assertNotIn("\x1b", output.getvalue())

    def test_arrows_enter_and_mode_restoration(self):
        master, slave = pty.openpty()
        stream = os.fdopen(os.dup(slave), "r")
        self.addCleanup(stream.close)
        self.addCleanup(os.close, slave)
        self.addCleanup(os.close, master)
        before = termios.tcgetattr(slave)
        result = []

        class Output(io.StringIO):
            def isatty(self):
                return True

        thread = threading.Thread(
            target=lambda: result.append(
                terminal.Terminal(stream, Output()).choose("Themes", ["Default", "New"])
            )
        )
        thread.start()
        for _ in range(100):
            if not termios.tcgetattr(slave)[3] & termios.ICANON:
                break
            time.sleep(0.005)
        os.write(master, b"\x1b[B\r")
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [1])
        self.assertEqual(termios.tcgetattr(slave), before)


if __name__ == "__main__":
    unittest.main()
