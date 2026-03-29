# Local ZMK Firmware Builds (Dockerized)

This setup provides a fast, containerized build environment for [ZMK Firmware](https://zmk.dev), allowing you to compile firmware locally without pushing changes to GitHub or installing any toolchains on your system.

- Rapid feedback loop for keymap and overlay changes
- No GitHub Actions delay
- No toolchain installation required
- Cross-platform, reproducible builds
- Automatic shield and keymap discovery from build.yaml
- Isolated build sandboxes per shield
- ZMK Studio USB-UART support on central shields
- Artifacts published by format and keymap to a persistent folder for easy access

---

## Quick Start

### 1. Prerequisites

Make sure you have:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- This repository cloned on your host machine

---

### 2. Start the Build Container

```bash
cd local-build
docker-compose run --rm builder
```

### 3. Firmware Output

Firmware files are placed under the `firmwares/` directory at the root of the repo, grouped by format and keymap. For example, with the default build.yaml:

```
firmwares/
├── charybdis_bt/
│   ├── qwerty/
│   │   ├── charybdis_left_bt.uf2
│   │   └── charybdis_right_bt.uf2
│   ├── colemak_dh/
│   │   ├── charybdis_left_bt.uf2
│   │   └── charybdis_right_bt.uf2
│   └── canary/
│       ├── charybdis_left_bt.uf2
│       └── charybdis_right_bt.uf2
├── charybdis_dongle/
│   ├── qwerty/
│   │   ├── charybdis_dongle.uf2
│   │   ├── charybdis_left_dongle.uf2
│   │   └── charybdis_right_dongle.uf2
│   ├── colemak_dh/ ...
│   └── canary/ ...
└── settings_reset.uf2
```

---

## Choosing What to Build

By default the build runs every keymap and every shield defined in `build.yaml`. To narrow down the build, edit `build.yaml` before running the container and comment out the entries you don't want.

To build only the dongle format with a single keymap, for example:

```yaml
include:
  # - name: bt
  #   ...

  - name: standard_dongle
    board: nice_nano//zmk
    shield:
      - charybdis_left_dongle
      - charybdis_right_dongle
      - charybdis_dongle
    keymap:
      - qwerty

  # - name: settings_reset
  #   ...
```

The same `build.yaml` drives both the local build and GitHub Actions, so these edits apply to both.

---

## Tips

### Drop into a shell for troubleshooting

This will give you an interactive bash prompt with all dependencies loaded, so you can run or debug the script manually:

```bash
docker-compose run --rm --entrypoint bash builder
```

Once inside the shell, you can execute the script manually, or go troubleshooting:

```bash
bash ./local-build/build_setup.sh
```

---

## Troubleshooting

- Enable USB logging to troubleshoot the firmware while it's running.
  - This is disabled by default since it has a significant negative impact on battery life.
  - To turn it on, set `ENABLE_USB_LOGGING="true"` at the top of [build_setup.sh](build_setup.sh), then follow instructions [here](https://zmk.dev/docs/development/usb-logging) to see the log stream on your computer.
  - Since this is a split keyboard you'll likely have to use `sudo tio /dev/ttyACM1` or `sudo tio /dev/ttyACM2` depending on what side you want to see logs for.
    - If you don't know what tty devices your system can see, run `ls -l /dev/serial/by-id` to find out.
    - To enable PMW3610 sensor debug logging, also uncomment `CONFIG_PMW3610_ALT_LOG_LEVEL_DBG=y` in the relevant shield conf:
      - BT mode: `boards/shields/charybdis_right_bt/charybdis_right_bt.conf`
      - Dongle mode: `boards/shields/charybdis_dongle/charybdis_dongle.conf`
- If the firmware is not generated as expected, use the interactive shell method above to inspect `/workspaces/zmk/firmwares` or rerun the script with debugging.
- Check the script output for any warnings or errors about missing shields, keymaps, or build failures. To save the output to a file:
  ```bash
  docker-compose run --rm builder > logs.txt 2>&1
  ```

---

## More Resources

- [ZMK Documentation](https://zmk.dev/docs)
- [ZMK Dev Container Setup](https://zmk.dev/docs/development/local-toolchain/setup/container)
