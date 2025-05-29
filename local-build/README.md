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

Firmware files will be placed under firmwares/ on your host, in subdirectories by keymap. Each file is named for the shield/side (e.g. charybdis_left.uf2). Example:

```bash
firmwares/
  qwerty/
    charybdis_left.uf2
    charybdis_right.uf2
  colemak_dh/
    charybdis_left.uf2
    charybdis_right.uf2
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

- If the firmware is not output as expected, use the shell method above to inspect `/workspaces/zmk-firmwares` or rerun the script with debugging.

- Check the script output for any warnings or errors about missing shields, keymaps, or build failures.

---

## 📚 More Resources

- [ZMK Documentation](https://zmk.dev/docs)
- [ZMK Dev Container Setup](https://zmk.dev/docs/development/local-toolchain/setup/container)
