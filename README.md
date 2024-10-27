[![.github/workflows/build.yml](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions/workflows/build.yml)

## Intro

This repository offers pre-configured ZMK firmware designed for Wireless Charybdis keyboards, supporting both the ubiquitous QWERTY layout and the optimized Colemak DH layout. You can choose from two configurations:

- Bluetooth and USB
- Dongle

Additionally, this repository also provides high level instructions and resources on how to customize and build the firmware to meet your specific needs.

## Usage

If you'd like to use the pre-built firmware the files can be found in the [Actions Workflows](https://github.com/280Zo/charybdis-wireless-mini-zmk-firmware/actions?query=is%3Acompleted+branch%3Amain). To download them, log into Github, click the link, select the latest run that passed on the main branch, and download the applicable firmware. There are five firmware artifacts to choose from. If you're unsure which one to use, you probably want the firmware-charybdis-qwerty build.

- **firmware-charybdis-qwerty** - Bluetooth/USB with QWERTY layout
- **firmware-charybdis-qwerty-dongle** - Dongle with QWERTY layout
- **firmware-charybdis-colemak** - Bluetooth/USB with Colemak DH layout
- **firmware-charybdis-colemak-dongle** - Dongle with Colemak DH layout
- **firmware-reset-nanov2** - Reset the firmware completely

There are a few things to note about how the pre-built firmware is configured:

- ZMK has terms for each side of a split keyboard. Central is the half that sends keyboard outputs over USB or advertises to other devices over bluetooth. Peripheral is the half that will only send keystrokes to the central once they are paired and connected through bluetooth. The Bluetooth/USB firmware uses the right side as central.
- The dongle firmware will have much better battery life for the central side, but requires an extra MCU and can only be connected through the dongle.
- The Bluetooth/USB firmware can connect through Bluetooth, but the central side will have a shorter battery life because it needs to maintain that connection.
  - The central side can also be plugged in to USB and the keyboard can be used when Bluetooth on the host computer isn't available (e.g. BIOS navigation)
- To add support for the PMW3610 low power trackball sensor, badjeff's [zmk-pmw3610-driver](https://github.com/badjeff/zmk-pmw3610-driver), [ZMK Input Behavior Listener](https://github.com/badjeff/zmk-input-behavior-listener?tab=readme-ov-file), and [ZMK Split Peripheral Input Relay](https://github.com/badjeff/zmk-split-peripheral-input-relay) modules are included in the firmware.
- eigatech's [zmk-configs](https://github.com/eigatech/zmk-config?tab=readme-ov-file) played a major role in getting badjeff's drivers and modules fully configured and are a great resource
- A separate branch builds the Bluetooth/USB firmware using [inorichi's driver](https://github.com/inorichi/zmk-pmw3610-driver?tab=readme-ov-file) as an alternative to badjeff's driver.
- [Petejohanson's individual work](https://github.com/petejohanson/zmk/blob/feat/pointers-move-scroll/docs/docs/behaviors/mouse-emulation.md) is also included in the build to allow mouse keys to function. This will be used until the main ZMK repo merges it.

## Flashing the Firmware

Follow the steps below to flash the firmware

- If you are flashing the firmware for the first time, or if you're switching between the dongle and the Bluetooth/USB configuration, flash the reset firmware to all the devices first
- Unzip the firmware.zip
- Plug the right half info the computer through USB
- Double press the reset button
- The keyboard will mount as a removable storage device
- Copy the applicable uf2 file into the NICENANO storage device (e.g. charybdis_qwerty_dongle.uf2 -> dongle)
- It will take a few seconds, then it will unmount and restart itself.
- Repeat these steps for all devices.
- You should now be able to use your keyboard

Note - If the keyboard halves aren't connecting as expected, try pressing the reset button on both halves at the same time. If that doesn't work, follow the [ZMK Connection Issues](https://zmk.dev/docs/troubleshooting/connection-issues#acquiring-a-reset-uf2) documentation for more troubleshooting steps.

## Keymaps & Layers

Each layer has been heavily influenced by [Miryoku](https://github.com/manna-harbour/miryoku/) and [home row mods](https://precondition.github.io/home-row-mods) that use [bilateral combinations](https://sunaku.github.io/home-row-mods.html) to make typing as efficient and comfortable as possible, though some non-bilateral key options are also included for optional usage.
To reduce hand movement, extra attention has also been given to making sure cursor, scrolling, and mouse button operations are as seamless as possible.

Review the layer maps below to see how each one functions. Then either modify the keymap to fit your needs, or start using these defaults to become more familiar with them.

Here are a few tips for a quick start:

- When moving the trackball, the mouse layer will be automatically activated. When the trackball movement stops, the previous layer is activated again.

- The bluetooth keys on the EXTRAS layer allow you to select which bluetooth pairing you want, BT-CLR clears the pairing on the selected profile.

- The most left thumb button has multiple functions
  - When held, the function of the trackball is changed from moving the cursor to scrolling.
  - When double tapped, it will reduce the cursor speed for more precision, and activate the mouse layer.
  - When single tapped it will activate the base layer.

![keymap images](keymap-drawer/charybdis.svg)

## Modify Key Mappings

### Use a GUI

Using a GUI to generate the keymap file content is the easiest option when getting started. Head over to nickcoutsos' keymap editor and follow the steps below.

- Fork/Clone this repo
- Open a new tab to the [keymap editor](https://nickcoutsos.github.io/keymap-editor/)
- Give it permission to see your repo
- Select the branch you'd like to modify
- Update the keys to match what you'd like to use on your keyboard
- Save
- Wait for the pipeline to run
- Download and flash the new firmware

### Edit Code Directly

To change a key layout choose a behavior you'd like to assign to a key, then choose a parameter code. This process is more clearly outlined on ZMK's [Keymaps & Behaviors](https://zmk.dev/docs/features/keymaps) page.

- Behaviors are all documented on the [Behaviors Overview](https://zmk.dev/docs/behaviors)
- Codes are all documented on the [keycodes](https://zmk.dev/docs/codes) page

Open the keymap file and change keys, or add/remove layers, then merge the changes and re-flash the keyboard with the updated firmware.

## Building Your Own Firmware

ZMK provides a comprehensive guide to follow when creating a [New Keyboard Shield](https://zmk.dev/docs/development/new-shield). I'll touch on some of the points here, but their docs should be what you reference when you're building your own firmware.

### File Structure

When building the ZMK firmware, the files need to be located in the correct place. The formats and locations of the files can be found on ZMK's [Configuration Overview](https://zmk.dev/docs/config).

### Mapping GPIO Pins to Keys

To set up some of the configuration files it requires a knowledge of which keys connect to which pins on the MCU (see the [Shield Overlays](https://zmk.dev/docs/development/new-shield#shield-overlays) section), and how the rows and columns are wired.

To get this information, look at the PCB kcad files and follow the traces from key pads, to row and column through holes, to MCU through holes. Once you have that information you can update the applicable dtsi/overlay files.

### Changing the Central and Peripheral Assignments

Follow the ZMK documentation to change the [Kconfig.deconfig](https://zmk.dev/docs/development/new-shield#kconfigdefconfig).

### Changing the Keyboard Name

Follow the ZMK [Kconfig.defconfig](https://zmk.dev/docs/development/new-shield#kconfigdefconfig) section to update the keyboard name. Make sure to read about the danger in exceeding the 16 character limit.

## Creating Graphical Key Maps

This repo uses the excellent work of caksoylar's [Keymap Drawer](https://keymap-drawer.streamlit.app/) to automatically generate a key mapping of each layer when the Github Actions are run.

## Upcoming ZMK Features

ZMK is actively being developed and there are a few features that will be added to these builds as soon as they are released.

- Mouse Pointer & Scrolling - [PR in review](https://github.com/zmkfirmware/zmk/pull/2027)
- Layer Locks - [Layer locks will hopefully get merged in](https://github.com/zmkfirmware/zmk/pull/1984)

## Credits

- [eigatech](https://github.com/eigatech)
- [badjeff](https://github.com/badjeff)
- [inorichi](https://github.com/inorichi)
- [manna-harbour](https://github.com/manna-harbour)
- [nickcoutsos](https://github.com/nickcoutsos/keymap-editor)
- [Petejohanson](https://github.com/petejohanson)
- [caksoylar](https://github.com/caksoylar/keymap-drawer)