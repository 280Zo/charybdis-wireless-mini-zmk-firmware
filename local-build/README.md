# 🛠️ Local ZMK Firmware Builds (Dockerized)

This setup provides a **fast, containerized build environment** for [ZMK Firmware](https://zmk.dev), allowing you to compile firmware locally without pushing changes to GitHub or installing any toolchains on your system.

- **Rapid feedback loop for keymap and overlay changes**
- **No GitHub Actions delay**
- **No toolchain installation required**
- **Cross-platform, reproducible builds**
- **Automatic shield and keymap discovery**
- **PMW3610 driver integration**
- **Isolated build sandboxes for each shield**
- **ZMK Studio USB-UART support**
- **Artifacts are published by keymap to a persistent folder for easy access**

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

Firmware files will be placed in under the firmwares directory in the root of the repo on your host. They will be grouped by format (bt/dongle) and keymap:

```bash
firmwares/
├── charybdis_bt
│   ├── colemak_dh
│   │   ├── charybdis_left.uf2
│   │   └── charybdis_right.uf2
│   ├── graphite
│   │   ├── charybdis_left.uf2
│   │   └── charybdis_right.uf2
│   └── qwerty
│       ├── charybdis_left.uf2
│       └── charybdis_right.uf2
├── charybdis_dongle
│   ├── colemak_dh
│   │   ├── charybdis_dongle.uf2
│   │   ├── charybdis_left.uf2
│   │   └── charybdis_right.uf2
│   ├── graphite
│   │   ├── charybdis_dongle.uf2
│   │   ├── charybdis_left.uf2
│   │   └── charybdis_right.uf2
│   └── qwerty
│       ├── charybdis_dongle.uf2
│       ├── charybdis_left.uf2
│       └── charybdis_right.uf2
└── settings_reset.uf2
```

---

## 💡 Tips

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
  - This is disabled by default since it has a significant negative impact on battery life
  - To turn it on, enable the variable at the top of the [build script](local-build/build_setup.sh), then follow instructions [here](https://zmk.dev/docs/development/usb-logging) to see the log stream on your computer.
  - If you don't know what tty device to use, run this command to find out `ls -l /dev/serial/by-id`
- If the firmware is not generated as expected, use the interactive shell method above to inspect `/workspaces/zmk-firmwares` or rerun the script with debugging.
- Check the script output for any warnings or errors about missing shields, keymaps, or build failures. If you'd like to save the script output to a file for local parsing in a text editor start the build container with this command:
  ```bash
  docker-compose run --rm builder > logs.txt 2>&1
  ```

---

## 📚 More Resources

- [ZMK Documentation](https://zmk.dev/docs)
- [ZMK Dev Container Setup](https://zmk.dev/docs/development/local-toolchain/setup/container)
