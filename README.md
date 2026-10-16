[![.github/workflows/build.yml](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions/workflows/build.yml)

## Intro

This repository offers pre-configured ZMK firmware. It's designed for the [Wireless Charybdis keyboards](https://github.com/280Zo/charybdis-wireless-mini-3x6-build-guide?tab=readme-ov-file), but is easily adaptable to other platforms. It uses a pinned ZMK development revision with Zephyr 4.1.0 + ZMK fixes, pending validation of the ZMK v0.4.0 release. It supports Bluetooth/USB split and dongle builds (including Prospector dongles with displays), with modular input listeners and processors for pointer and scroll behavior.

### Pinned build baseline

The authoritative dependency pins are in [config/west.yml](config/west.yml):

| Component | Selected revision |
| --- | --- |
| ZMK development snapshot | [`4dd95d7`](https://github.com/zmkfirmware/zmk/commit/4dd95d7840eb3d5a3f59bb29fbf1ab054715ef85) |
| Zephyr 4.1.0 + ZMK fixes | [`10ba6d0`](https://github.com/zmkfirmware/zephyr/commit/10ba6d0cb38bc3d258775d27982f707599320085) |
| Existing PMW3610 driver | [`f6e2343`](https://github.com/280Zo/zmk-pmw3610-driver/commit/f6e234367b22508b5c0a6bcc82437c64f320089b) |
| Prospector screen module | [`b6f5d2e`](https://github.com/280Zo/prospector-zmk-module/commit/b6f5d2e81516db1c76743838b8a86af2c2a4c0fc) |

Zephyr is explicitly pinned rather than following the branch imported by ZMK.

> **Why not the latest official Zephyr release?** This repo prefers the latest
> official releases, but ZMK doesn't yet support upstream Zephyr 4.4.x. A test
> build against Zephyr v4.4.2 failed before compiling: Zephyr 4.4 requires a
> `full_name` field in every board definition, and ZMK's own boards (including the
> nice!nano) don't have one yet. ZMK, including its latest `main`, still builds with
> its maintained Zephyr branch `v4.1.0+zmk-fixes`. The pinned Zephyr above is the
> head of that branch, which is the version ZMK supports and the version
> hardware-tested here. This is a deliberate exception, to be revisited when ZMK
> v0.4.0 is released or ZMK moves to a newer Zephyr.

The local build container is pinned by digest in
[local-build/docker-compose.yml](local-build/docker-compose.yml). Normal dependency
updates retrieve these selected revisions; they do not adopt newer upstream code.

The tested hardware configuration is the Colemak layout with both dongle-connected
halves and the no-sensor Prospector dongle (Operator, diagnostics, Keyboard Knight
and hidden-extra enabled). The standard dongle was compile-checked; sensor hardware
validation remains separate. ZMK v0.4.0 will be evaluated before switching to its
release tag. Pins are updated manually after testing, not automatically.

## Overview & Usage

<!-- ![stacked keymap](keymap-drawer/stacked/stacked.svg)
![combos keymap](keymap-drawer/stacked/combos.svg) -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="keymap-drawer/stacked/stacked-combos-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="keymap-drawer/stacked/stacked-combos-light.png">
  <img alt="stacked-combos keymap" src="keymap-drawer/stacked/stacked-combos-dark.png">
</picture>


To see all the layers check out the [full render](keymap-drawer/all_layers/all_layers.svg).


**Keyboard Layers**
| # | Layer      | Purpose                                                          |
| - | ---------- | ---------------------------------------------------------------- |
| 0 | **BASE**   | Standard typing with timeless home-row mods                      |
| 1 | **NUM**    | Combined digits + F-keys (tap for numbers, shift for functions)  |
| 2 | **NAV**    | Arrow keys, paging, TMUX navigation, mouse pointer               |
| 3 | **SYM**    | Symbols, punctuation, and a couple of helpers                    |
| 4 | **GAME**   | Gaming layer (just key-codes, no mods)                           |
| 5 | **EXTRAS** | Shortcuts, functions & snippets                                  |
| 6 | **MOUSE**  | Full mouse-key layer (pointer + wheel)                           |
| 7 | **SLOW**   | Low-speed pointer for precision pointer                          |
| 8 | **SCROLL** | Vertical/Horizontal scroll layer                                 |


**Home-Row Mods**
| Side                | Hold = Modifier              | Tap = Letter / Key  |
| ------------------- | ---------------------------- | ------------------- |
| Left                | **Gui / Alt / Shift / Ctrl** | `A S D F`           |
| Right               | **Ctrl / Shift / Alt / Gui** | `J K L ;`           |


**Combos**
| Trigger Keys              | Result                                  |
| ------------------------- | --------------------------------------  |
| `K17 + K18`                | **Caps Word** (one-shot words in CAPS) |
| `K25 + K26`                | **Left Mouse Button**                  |
| `K26 + K27`                | **Middle Mouse Button**                |
| `K27 + K28`                | **Right Mouse Button**                 |
| `K13 + K22`                | Toggle **MOUSE** layer                 |
| `K38 + K39` (thumb cluster)| Layer-swap **BASE / EXTRAS**           |


**Other Highlights**
- This repo now includes builds for the **[Prospector ZMK screen dongle](https://github.com/carrefinho/prospector)**.
  - Suppoert for the Nice!Nano v2 has been added to the firmware options.
  - The prospector case has been adapted in [OnShape](https://cad.onshape.com/documents/1ab8632c0729c14a80991694/w/0a5575e0aa91142d15642877/e/053f9ce9786904291254a911) to fit the Nice!Nano v2.
  Options are also available for the smaller APDS9960 ambient light sensor variant, and a lower-cost Waveshare non-touch screen option (SKU 24382)
  - APDS9960 sensor builds use a custom Prospector module ALS-only driver that works with the various APDS9960 sensor types.
- **Timeless-inspired home row mods:** Based on [urob's](https://github.com/urob/zmk-config#timeless-homerow-mods) work and configured on the BASE layer.
- **Thumb-scroll mode:** Hold the left-most thumb button (K36) while moving the trackball to turn motion into scroll.
- **Precision cursor mode:** Double-tap, then hold K36 to drop the pointer speed, release to return to normal speed.
- **K37 - Multifunction**
  - Tap: Left mouse click
  - Tap & Hold: Layer 3 (symbols) while the key is held
  - Double-Tap & Hold: holds the left mouse button
  - Tripple-Tap: Double mouse click
- **K38 - Multifunction**
  - Tap: Backspace
  - Hold: Layer 1 (numbers) while the key is held
  - Quick tap, then hold: Repeats Backspace instead of dropping into Layer 1
- **Bluetooth profile quick-swap:** Jump to the EXTRAS layer and tap the dedicated BT-select keys to pair or switch among up to four saved hosts (plus BT CLR to forget all).
- **Prospector display brightness controls:** Prospector builds can toggle between ambient-light and manual brightness control from the EXTRAS layer. On Colemak-DH, K04 brightens, K15 toggles auto/manual, and K16 dims.
- **PMW3610 low power trackball sensor driver:** Provided by [badjeff](https://github.com/badjeff/zmk-pmw3610-driver)
  - Patched to prevent cursor jump on wake
- **Hold-tap side-aware triggers:** Each HRM key only becomes a modifier if the opposite half is active, preventing accidental holds while one-handed.
- **Timeless HRM with selective exceptions:** Base home-row mods use the timeless-style `balanced + hold-trigger-on-release` setup, while A, I, and O (on a Colemak-DH layout) keep tap-preferred variants to reduce accidental mod triggers during fast rolls.
- **ZMK Studio:** Supported on Bluetooth and the standard no-screen dongle builds for quick keymap adjustments. Prospector screen builds disable it to preserve RAM.


## Flash the Firmware

Download your choice of firmware from the Releases page. Choose a combination of format (Bluetooth/Dongle) and layout (QWERTY, etc.), then follow the steps below to flash it to your keyboard

1. Unzip the firmware bundle
2. One at a time, plug the devices into the computer through USB
3. Double press the reset button on the nice!nano
4. The keyboard will mount as a removable storage device
5. Copy the applicable uf2 file into the storage device
6. It will take a moment, then it will unmount and restart itself.
7. Repeat these steps for all devices.
8. If you've flashed one of the prospector dongle builds, the halves can be powered on in any order. Each half tells the dongle whether it's the left or right side, so the battery widget always shows them on the correct side.

> [!NOTE]
> If you are flashing the firmware for the first time, or if you're switching between the dongle and the Bluetooth/USB configuration, flash the reset firmware to all the devices first


## Customization

### Modify Key Mappings

**ZMK Studio**

[ZMK Studio](https://zmk.studio/) allows users to update functionality during runtime. It is supported on Bluetooth builds and the standard no-screen dongle build. For more details on how to use ZMK Studio, refer to the [ZMK documentation](https://zmk.dev/docs/features/studio).

> [!NOTE]
> Prospector screen builds disable ZMK Studio to preserve RAM and improve stability with the display stack.


**Edit Keymap Directly**

To change a key layout, choose a behavior you'd like to assign to a key, then choose a parameter code. This process is more clearly outlined on ZMK's [Keymaps & Behaviors](https://zmk.dev/docs/features/keymaps) page. All keycodes are documented [here](https://zmk.dev/docs/codes).

Modify the [qwerty.keymap](config/keymaps/qwerty.keymap) or one of the behaviors, combos, or macros in the [keymap_features](config/keymap_features) folder, then follow the instructions below to build and flash the firmware to your keyboard.

### Modifying Trackball Behavior

The trackball uses ZMK's modular input processor system, making it easy to adjust pointer behavior to your liking. All trackball-related configurations and input processors are conveniently grouped in the [charybdis_pointer.dtsi](config/trackball/charybdis_pointer.dtsi) file. Modify this file to customize tracking speed, acceleration, scrolling behavior, etc. Then rebuild your firmware.

### Modify Build Format Selection

Build formats are also selected in [build.yaml](build.yaml).

To change which firmware families are built:

1. Open [build.yaml](build.yaml)
2. Find the build entry or entries you want to keep
3. Comment out or remove the entries you do not want

The main build families are:

- `bt`: Bluetooth split builds
- `dongle_standard_nano`: the default no-screen dongle builds
- `dongle_prospector_*`: screen-enabled dongle builds using the Prospector adapter

For any of the Prospector dongle firmwares, there are additional customization options.

To change the Prospector layout:

1. Open [build.yaml](build.yaml)
2. Find the Prospector build entry you want
3. Replace the selected file under `extra_conf_files` with a different layout file from [config/dongle_prospector_layouts](config/dongle_prospector_layouts)

To change the Radii theme:

1. Select `dongle_prospector_layout_radii.conf` in `extra_conf_files`
2. Add one theme overlay from [config/dongle_prospector_themes](config/dongle_prospector_themes) to `extra_dtc_overlay_files`

For Prospector builds with the APDS9960 ambient light sensor, [config/dongle_prospector/dongle_prospector_sensor.conf](config/dongle_prospector/dongle_prospector_sensor.conf) intentionally turns off Zephyr's stock APDS9960 driver and enables the Prospector module's replacement driver:

```conf
CONFIG_APDS9960=n
CONFIG_PROSPECTOR_APDS9960=y
```

That keeps the application using the normal Zephyr sensor API while letting the Prospector module provide the APDS9960 behavior needed for variations in the APDS9960 sensors.

To change Prospector display feature selection:

1. Open [build.yaml](build.yaml)
2. Find the Prospector display build entry you want
3. Add or remove feature files under `extra_conf_files`

Available Prospector display feature files:

- [config/dongle_prospector_features/dongle_prospector_feature_diagnostics.conf](config/dongle_prospector_features/dongle_prospector_feature_diagnostics.conf): enables the swipe/key-selectable diagnostics page.
- [config/dongle_prospector_features/dongle_prospector_feature_keyboard_knight.conf](config/dongle_prospector_features/dongle_prospector_feature_keyboard_knight.conf): enables Keyboard Knight, an animated WASD knight avatar that sleeps at rest, guards during normal typing, and charges during fast typing.
- [config/dongle_prospector_features/dongle_prospector_feature_hidden_extra.conf](config/dongle_prospector_features/dongle_prospector_feature_hidden_extra.conf): enables the optional hidden display extra.

> [!NOTE]
> Local builds with `ENABLE_USB_LOGGING=true` automatically skip Prospector display feature files under `config/dongle_prospector_features/`. The base Prospector display/layout still builds, but diagnostics, Keyboard Knight, and the hidden extra are omitted so the logging firmware stays flashable on the nice!nano.

### Modify Keymap Selection

Keymaps live in [config/keymaps](config/keymaps) and are selected in [build.yaml](build.yaml).

To change which keymaps are built:

1. Open [build.yaml](build.yaml)
2. Find the `keymap:` list under the build entry you have picked
3. Keep the keymaps you want and comment out or remove the others

### Build the Firmware

To build the firmware follow either of the build processes below:

**Local Build - Single Command**

1. Clone this repo
2. Update the config files to match your use case
3. Follow the instructions in the [local-build README](local-build/README.md)
4. Firmwares will be available in the firmwares folder

**Pipeline Build - GitHub Actions**

1. Fork this repo
2. Update the config files to match your use case
3. Push changes and confirm the workflows are running
4. Firmwares will be available in the action artifacts


## Credits

- [badjeff](https://github.com/badjeff) for the PMW3610 ZMK driver used as the basis for the trackball sensor integration
- [carrefinho](https://github.com/carrefinho) for the original [Prospector](https://github.com/carrefinho/prospector) hardware and the [Prospector ZMK module](https://github.com/carrefinho/prospector-zmk-module/tree/feat/new-status-screens) this repo adapts for Charybdis dongles
- [eigatech](https://github.com/eigatech) for prior Charybdis dongle work and useful reference patterns around split trackball/input-listener integration
- [nickcoutsos](https://github.com/nickcoutsos/keymap-editor) for the browser-based keymap editor workflow
- [caksoylar](https://github.com/caksoylar/keymap-drawer) for the keymap rendering workflow and physical layout conversion tooling
- [urob](https://github.com/urob/zmk-config#timeless-homerow-mods) for the timeless home-row mod approach this keymap builds on and the stacked layer SVG inspiration
