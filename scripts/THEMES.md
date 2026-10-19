# Operator theme creator

Run `python3 scripts/theme-tweak.py` from this repository (or invoke its absolute
path from anywhere). Python 3 and a compatible Prospector module checkout are
required; no Python packages are installed.

Theme-specific files are grouped as follows; unrelated repository scripts are unchanged:

```text
scripts/
  theme-tweak.py       # launcher
  theme_editor/        # helper package
  theme-previews/      # generated images, backups and renderer cache (Git-ignored)
  tests/              # tests
```

The preview directory is created on first use after confirmation. Existing outputs
under `local-build/theme-previews/` are not moved or deleted.

The default module source is `prospector-zmk-module/`, populated by the existing
build setup. Use `--module PATH` to explicitly choose a different checkout for
editing/preview. That does **not** change the module used by the firmware builder.
Paths are displayed relative to the repository or with neutral aliases such as
`<module>`, never as personal home-directory paths. A checkout with older,
unsupported palette definitions is rejected.

## Flow

- Use **↑/↓ and Enter** to choose a theme or **New**. New themes start with an
  independent copy of Default; the menu stays simple.
- A paired colour/element-description table appears above the edit controls.
- **Edit colour** makes that same table selectable: **↑/↓** moves rows,
  **←/→** moves columns and **Enter** edits the highlighted colour. It scrolls
  within the terminal; narrow screens keep the same single-column fallback.
  Line mode uses the numbers shown in the table. Background stays fixed black.
  After changing a colour, the table stays active with the cursor retained so you
  can select another. **s** opens the normal save confirmation; cancelling it
  returns to the table at the same highlight. **q** leaves colour editing while
  keeping pending changes for the existing Save/Discard/Cancel flow.
  **p** generates a static Preview directly from this table, including unsaved
  edits; press Enter afterward to resume at the same highlighted colour.
  Enter `#RRGGBB`, `0xRRGGBB` or `RRGGBB`; WPM bars and the WPM number are separate
  table entries, not a hidden combined setting.
- **Import JSON** applies a validated colour set to the current pending theme.
- **Preview** generates a static image of the pending colours without saving the
  theme. It shows progress, then the image path, and waits for Enter so the result
  does not scroll away. **Save** shows the pending diff/preview and asks first.
- **Build**, inside a theme, opens the full inclusion checklist, with **Select all**
  and **Clear**. At least one theme is required. **Done** confirms startup/selection
  before generating build input. Excluded themes remain saved.
- **q** quits a clean session. Unsaved edits offer **Save / Discard / Cancel**;
  **Back** returns to theme selection. Dirty Build resolves pending edits first.
- Non-TTY input/output uses numbered line-mode menus. NO_COLOR disables colour
  escapes; narrow terminals use a single colour/description column pair.

Themes live in `config/dongle_prospector_operator_themes/themes.json`. Each custom
theme has a stable identity separate from its name. Built-in edits are stored as
overrides: source palettes are never rewritten. The final confirmed selection
generates `operator_themes.generated.h` beside the JSON; this build-required asset
must travel with your config. Do not edit the generated header by hand.

The configured startup theme is preserved when included. Otherwise the first
included theme starts. Saved choices survive recolouring and reordering; removing
the saved theme falls back to startup. The first flash with identity-based storage
ignores old positional preferences once, without requiring a settings reset.

Names currently allow 1–24 ASCII letters/digits/spaces/hyphens/underscores. Black
backgrounds and box styling are not colour-editable. Editing Ember preserves its
rounded/translucent boxes; new themes copy Default's metadata as well as colours.

## Preview and safety

The script asks before creating its preview/backup directory (default:
`scripts/theme-previews/`, ignored by Git). Preview is a normal image file: **no server,
localhost address, browser connection or background live updates**. Open the
printed file in an image viewer or browser. The full absolute image path and an
encoded `file://` link are printed at runtime for convenient opening; these paths
are not hardcoded into source or saved theme data. It remains available after the editor
exits. Choose Preview again after edits to generate a new image; nothing is opened
automatically.

With a compatible module, local CMake/compiler and the existing repository LVGL
checkout, Preview generates a high-quality PNG using the actual 280x240 production
widgets/fonts at 2x scale, including stats and the system-layer modifier row.
First render compiles the host harness; subsequent requested previews reuse LVGL
and rebuild the palette-dependent object. Editing alone never invokes the renderer.
It never prepares/downloads dependencies or changes saved firmware input. This is
an LVGL screenshot, not a calibrated simulation of the physical panel.

If dependencies are unavailable, Preview explicitly labels an approximate SVG
fallback instead. If rendering fails, it reports failure and does not save the
theme or claim a new image is ready. Source/backup messages retain neutral aliases;
only the generated image location is printed in full, as requested.

Each save backs up the previous input. Cancelling before saving changes no theme
data; preview files may remain. Concurrent file changes abort rather than overwrite
them. Final library/header activation rolls back its own writes on failure.

## JSON import

Accepts either a complete palette object in the same shape as a `custom[]` entry,
or a complete version-1 `themes.json` library (choose a theme from that library).
Only its colours are applied to the current pending theme: current ID, name,
box styling, other themes and build selection are preserved. Review and confirm
application, then save separately. There is no implicit merge/library replacement.

Inputs must be regular UTF-8 JSON files, at most 1 MiB, with at most 16 nesting
levels and 256 themes/selected IDs. Duplicate keys, unknown fields, nonstandard
numbers, invalid types/IDs/colours and non-black backgrounds are rejected. URLs,
symlinks, pipes/devices and sensitive credential filenames are not read. Paths are
not expanded as shell commands or environment variables. YAML is not supported;
no YAML package is required.

## Build integration status

**Automatic building is deliberately gated.** The existing entry point remains
`local-build/docker-compose.yml` → `local-build/build_setup.sh`. It needs a
prepared/offline, preserve-output handoff before this helper can safely invoke it.
The helper does not call local recovery scripts or invent another builder.

The module actually used by that builder must contain generated-registry support;
an older manifest pin will not consume the new input. Do not assume selecting a
sibling checkout with `--module` updates the build checkout. Until those prerequisites
are ready, saving and previewing work, but requesting a build reports the blocker
and returns exit status 2. It does not run Docker or publish firmware.

Unit tests: `python3 -B -m unittest discover -s scripts/tests`.
Optional compile checks: set `OPERATOR_THEME_TEST_MODULE` to a compatible module
checkout and rerun that command with a local C compiler available.
For real screenshot pixel checks, also set `OPERATOR_THEME_RENDER_LVGL` to the local
LVGL checkout. Renderer artifacts are private generated output, not commit inputs.
