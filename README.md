[![.github/workflows/build.yml](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions/workflows/build.yml)

## Intro

This repository offers pre-configured ZMK firmware designed for [Wireless Charybdis keyboards](https://github.com/280Zo/charybdis-wireless-mini-3x6-build-guide?tab=readme-ov-file). It supports both Bluetooth/USB and Dongle configurations and uses the latest input listener and processors to act as a bridge between the trackball and the rest of the system.

If you want to customize things the repo is set up to build through GitHub Actions (just clone and run it), or you can use the
containerized build script that will build all firmwares locally with a single command.


## Quick Start

### Flashing the Firmware

Download your choice of firmware from the Releases page. Choose a combination of format (Bluetooth/Dongle) and layout (QWERTY, etc.), then follow the steps below to flash it to your keyboard

1. Unzip the firmware zip
2. Plug the right half into the computer through USB
3. Double press the reset button
4. The keyboard will mount as a removable storage device
5. Copy the applicable uf2 file into the NICENANO storage device (e.g. charybdis_qwerty_dongle.uf2 -> dongle)
6. It will take a few seconds, then it will unmount and restart itself.
7. Repeat these steps for all devices.
8. You should now be able to use your keyboard

> [!NOTE]  
> If you are flashing the firmware for the first time, or if you're switching between the dongle and the Bluetooth/USB configuration, flash the reset firmware to all the devices first

### Dongle Options

There are two dongle families in this repo:

- `standard_dongle`: the default no-screen dongle build
- `dongle_prospector_*`: screen-enabled dongle builds based on a forked `prospector-zmk-module`

The screen-enabled builds in this repo are a forked adaptation of [carrefinho's Prospector ZMK module](https://github.com/carrefinho/prospector-zmk-module/tree/feat/new-status-screens), extended to support both:

- the original XIAO BLE-based Prospector MCU
- a nice!nano v2-based dongle stack

This fork also supports both Waveshare 1.69" screen variants for the Prospector:

- touch screen: SKU `27057`
- non-touch screen: SKU `24382`

The standard no-screen dongle is still the simplest and most stable option if you do not need a display.

#### Build Variants

The build matrix in [build.yaml](build.yaml) currently includes:

| Build Name | Screen | Dongle MCU | Ambient Light Sensor |
| ---------- | ------ | ---------- | -------------------- |
| `standard_dongle` | No | nice!nano v2 | N/A |
| `dongle_prospector_no_sensor` | Yes | nice!nano v2 | No |
| `dongle_prospector_sensor` | Yes | nice!nano v2 | Yes |
| `dongle_prospector_xiao_no_sensor` | Yes | XIAO BLE | No |
| `dongle_prospector_xiao_sensor` | Yes | XIAO BLE | Yes |

#### Prospector Layouts and Themes

Prospector layout selection is controlled by extra config fragments in [config/dongle_prospector_layouts](config/dongle_prospector_layouts).

Available layouts:

- `dongle_prospector_layout_classic.conf`
- `dongle_prospector_layout_field.conf`
- `dongle_prospector_layout_operator.conf`
- `dongle_prospector_layout_radii.conf`

`Operator` is the current default Prospector layout in this repo.

Radii supports optional color themes from [config/dongle_prospector_themes](config/dongle_prospector_themes):

- `dongle_prospector_theme_blue.overlay`
- `dongle_prospector_theme_green.overlay`
- `dongle_prospector_theme_red.overlay`
- `dongle_prospector_theme_purple.overlay`

To change the Prospector layout:

1. Open [build.yaml](build.yaml)
2. Find the Prospector build entry you want
3. Replace the selected file under `extra_conf_files` with a different layout file from [config/dongle_prospector_layouts](config/dongle_prospector_layouts)

To change the Radii theme:

1. Select `dongle_prospector_layout_radii.conf` in `extra_conf_files`
2. Add one theme overlay from [config/dongle_prospector_themes](config/dongle_prospector_themes) to `extra_dtc_overlay_files`

#### Prospector Shared Settings

Shared Prospector settings live in [config/dongle_prospector](config/dongle_prospector).

These files control:

- shared Prospector options
- sensor vs no-sensor behavior
- display idle blanking
- RAM-saving display settings

> [!NOTE]  
> ZMK Studio is intentionally disabled on Prospector builds to preserve RAM and reduce instability risk with the display stack.

### Overview & Usage

![keymap base](keymap-drawer/base/qwerty.svg)

To see all the layers check out the [full render](keymap-drawer/qwerty.svg).

**Keyboard Layers**
| # | Layer      | Purpose                                                          |
| - | ---------- | ---------------------------------------------------------------- |
| 0 | **BASE**   | Standard typing with timeless home-row mods                      |
| 1 | **NUM**    | Combined digits + F-keys (tap for numbers, hold for functions)   |
| 2 | **NAV**    | Arrow keys, paging, TMUX navigation, mouse pointer               |
| 3 | **SYM**    | Symbols, punctuation, and a couple of helpers                    |
| 4 | **GAME**   | Gaming layer (just key-codes, no mods)                           |
| 5 | **EXTRAS** | Shortcuts, functions & snippets                                  |
| 6 | **MOUSE**  | Full mouse-key layer (pointer + wheel)                           |
| 7 | **SLOW**   | Low-speed pointer for pixel-perfect work                         |
| 8 | **SCROLL** | Vertical/Horizontal scroll layer                                 |

**Home-Row Mods**
| Side                | Hold = Modifier              | Tap = Letter / Key  |
| ------------------- | ---------------------------- | ------------------- |
| Left                | **Gui / Alt / Shift / Ctrl** | `A S D F`           |
| Right               | **Ctrl / Shift / Alt / Gui** | `J K L ;`           |


**Combos**
| Trigger Keys              | Result                                 |
| ------------------------- | -------------------------------------- |
| `K17 + K18`               | **Caps Word** (one-shot words in CAPS) |
| `K25 + K26`               | **Left Click**                         |
| `K26 + K27`               | **Middle Click**                       |
| `K27 + K28`               | **Right Click**                        |
| `K13 + K22`               | Toggle **MOUSE** layer                 |
| `K38 + K39` (thumb cluster)| Layer-swap **BASE / EXTRAS**           |


**Other Highlights**
- **Timeless home row mods:** Based on [urob's](https://github.com/urob/zmk-config#timeless-homerow-mods) work and configured on the BASE layer with balanced flavor on both halves (280 ms tapping-term, and quick-tap with prior-idle tuning).
- **Thumb-scroll mode:** Hold the left-most thumb button (K36) while moving the trackball to turn motion into scroll.
- **Precision cursor mode:** Double-tap, then hold K36 to drop the pointer speed, release to return to normal speed.
- **Mouse-Click + Symbol-Layer - K37**
  - Tap: Left mouse click
  - Tap & Hold: Layer 3 (symbols) while the key is held
  - Double-Tap & Hold: holds the left mouse button
  - Tripple-Tap: Double mouse click
- **Backspace + Number-Layer - K38**
  - Tap: Backspace
  - Hold: Layer 1 (numbers) while the key is held
  - Double-Tap & Hold: Keeps Backspace held
- **Bluetooth profile quick-swap:** Jump to the EXTRAS layer and tap the dedicated BT-select keys to pair or switch among up to four saved hosts (plus BT CLR to forget all).
- **PMW3610 low power trackball sensor driver:** Provided by [badjeff](https://github.com/badjeff/zmk-pmw3610-driver)
  - Patched to remove build warnings and prevent cursor jump on wake
- **Hold-tap side-aware triggers:** Each HRM key only becomes a modifier if the opposite half is active, preventing accidental holds while one-handed.
- **Quick-tap / prior-idle:** Tuned for faster mod-vs-tap detection.
- **ZMK Studio:** Supported on Bluetooth and the standard no-screen dongle builds for quick keymap adjustments. Prospector screen builds disable it to preserve RAM.


## Customize Keymaps, Layers, & Trackball

This section will help you personalize your firmware. Everything, from keys and layers to advanced trackball behaviors, can easily be customized, even if you're new to ZMK.


### Building Your Customized Firmware

You can easily build the firmware locally or leverage GitHub Actions:

**Local Build (recommended for quick testing and debugging)**

Clone this repo, then run these commands from the repo root:
```sh
cd local-build
docker-compose run --rm builder
```
See the [local build README](local-build/README.md) for additional details, including how to enable USB logging in the builds.

**GitHub Actions**

- Fork or clone this repo
- Push your changes to your GitHub
- GitHub Actions automatically builds your firmware and publishes downloadable artifacts under the Actions tab.

### Build Format Selection

Build formats are also selected in [build.yaml](build.yaml).

To change which firmware families are built:

1. Open [build.yaml](build.yaml)
2. Find the build entry or entries you want to keep
3. Comment out or remove the entries you do not want

The main build families are:

- `bt`: Bluetooth split builds
- `standard_dongle`: the default no-screen dongle builds
- `dongle_prospector_*`: screen-enabled dongle builds using the Prospector adapter

In practice, most customization comes down to choosing:

- which build family to include
- which keymap names to keep in that build entry (instructions below)
- which Prospector layout/theme files to reference (if you are building a screen-enabled dongle)

### Keymap Selection

Keymaps live in [config/keymaps](config/keymaps) and are selected in [build.yaml](build.yaml).

To change which keymaps are built:

1. Open [build.yaml](build.yaml)
2. Find the `keymap:` list under the build entry you care about
3. Keep the keymaps you want and comment out or remove the others

To create or edit a keymap:

- edit one of the existing files in [config/keymaps](config/keymaps)
- or add a new `your_layout.keymap` file there, then add its name to the relevant `keymap:` list in [build.yaml](build.yaml)

### Modify Key Mappings

**ZMK Studio**

[ZMK Studio](https://zmk.studio/) allows users to update functionality during runtime. It is supported on Bluetooth builds and the standard no-screen dongle build.

> [!NOTE]
> Prospector screen builds disable ZMK Studio to preserve RAM and improve stability with the display stack.

To change the visual layout of the keys, the physical layout must be updated. This is the charybdis-layouts.dtsi file, which handles the actual physical positions of the keys. Though they may appear to be similar, this is different than the matrix transform file (charybdis.json) which handles the electrical matrix to keymap relationship.

To easily modify the physical layout, or convert a matrix transform file, [caksoylar](https://github.com/caksoylar/zmk-physical-layout-converter) has built the [ZMK physical layouts converter](https://zmk-physical-layout-converter.streamlit.app/).

For more details on how to use ZMK Studio, refer to the [ZMK documentation](https://zmk.dev/docs/features/studio).

**Keymap GUI**

Using a GUI to generate the keymap file before building the firmware is another easy way to modify the key mappings. Head over to nickcoutsos' keymap editor and follow the steps below.

- Fork/Clone this repo
- Open a new tab to the [keymap editor](https://nickcoutsos.github.io/keymap-editor/)
- Give it permission to see your repo
- Select the branch you'd like to modify
- Update the keys to match what you'd like to use on your keyboard
- Save
- Wait for the pipeline to run
- Download and flash the new firmware

**Edit Keymap Directly**

To change a key layout choose a behavior you'd like to assign to a key, then choose a parameter code. This process is more clearly outlined on ZMK's [Keymaps & Behaviors](https://zmk.dev/docs/features/keymaps) page. All keycodes are documented [here](https://zmk.dev/docs/codes).

Open the [qwerty.keymap](config/keymaps/qwerty.keymap) file and change keys, or add/remove layers, then merge the changes and re-flash the keyboard with the updated firmware. All of the behaviors, combos, and macros are in the [keymap_features](config/keymap_features) folder.


### Modifying Trackball Behavior

The trackball uses ZMK's modular input processor system, making it easy to adjust pointer behavior to your liking. All trackball-related configurations and input processors are conveniently grouped in the [charybdis_pointer.dtsi](config/trackball/charybdis_pointer.dtsi) file. Modify this file to customize tracking speed, acceleration, scrolling behavior, etc. Then rebuild your firmware.


### Troubleshooting

- If the keyboard halves aren't connecting as expected, try pressing the reset button on both halves at the same time. If that doesn't work, follow the [ZMK Connection Issues](https://zmk.dev/docs/troubleshooting/connection-issues#acquiring-a-reset-uf2) documentation for more troubleshooting steps.
- If you run into a bug or something’s not working, feel free to open an issue or submit a PR! Just keep in mind I'm not a developer, and this is a hobby project so I may not be able to fix everything.


## Credits

- [badjeff](https://github.com/badjeff) for the PMW3610 ZMK driver used as the basis for the trackball sensor integration
- [carrefinho](https://github.com/carrefinho) for the original [Prospector](https://github.com/carrefinho/prospector) hardware and the [Prospector ZMK module](https://github.com/carrefinho/prospector-zmk-module/tree/feat/new-status-screens) this repo adapts for Charybdis dongles
- [eigatech](https://github.com/eigatech) for prior Charybdis dongle work and useful reference patterns around split trackball/input-listener integration
- [nickcoutsos](https://github.com/nickcoutsos/keymap-editor) for the browser-based keymap editor workflow
- [caksoylar](https://github.com/caksoylar/keymap-drawer) for the keymap rendering workflow and physical layout conversion tooling
- [urob](https://github.com/urob/zmk-config#timeless-homerow-mods) for the timeless home-row mod approach this keymap builds on
