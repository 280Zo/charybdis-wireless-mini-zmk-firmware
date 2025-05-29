# for a bash prompt
docker-compose run --rm --entrypoint bash builder
- Then execute the script?

# for no bash prompt
docker-compose run --rm builder



---

# 🛠️ Local ZMK Firmware Builds (Dockerized)

This setup provides a **fast, containerized build environment** for [ZMK Firmware](https://zmk.dev), allowing you to compile firmware locally without pushing changes to GitHub or installing any toolchains on your system.

> ✅ Rapid feedback loop for keymap and overlay changes  
> ✅ No GitHub Actions delay  
> ✅ No toolchain installation required  
> ✅ Cross-platform, reproducible builds

---

## Quick Start

### 1. Prerequisites

Make sure you have:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- `git submodule add https://github.com/zmkfirmware/zmk.git zmk` to add zmk to this repo if it's not already there

The cloned repo will contain:
- `zmk/` → full ZMK source repo
- `config/` → keymaps, macros, combos, behaviors, other configs, etc.
- `boards/` → boards, shileds, overlays, other dts files, etc.
- `local-build/` → build configuration, `docker-compose.yml`, this README

---

### 2. Start a Shell in the ZMK Build Container

```bash
cd local-build
docker-compose run --rm builder bash
```

Once inside the container, initialize the ZMK workspace:

```bash
cd /workspaces/zmk
west init -l app
west update
west zephyr-export
```

---

### 3. Build Your Firmware

```bash
west build -s app -b <BOARD> \
  -- \
    -DZMK_CONFIG=/workspaces/zmk-config \
    -DZMK_EXTRA_MODULES=/workspaces/zmk \
    -DSHIELD=<SHIELD>
```

Examples:

```bash
## right side in bluetooth format
west build -p -d build/right-bt -s app -b nice_nano_v2 \
  -- \
    -DSHIELD=charybdis_right \
    -DDTS_EXTRA_CPPFLAGS="-I/workspaces/zmk-config -I/workspaces/zmk/app/include" \
    -DZMK_CONFIG=/workspaces/zmk-config
    -DZMK_EXTRA_MODULES=/workspaces/zmk \
    -DZEPHYR_EXTRA_DTC_OVERLAY_FILE="/workspaces/zmk-config/config/boards/shields/charybdis_right_host.dtsi"



## right side in dongle format


## left side


## dongle


## reset

```
>When building for a new board and/or shield after having built one previously, you may need to enable the pristine build option. This option removes all existing files in the build directory before regenerating them, and can be enabled by adding either --pristine or -p to the command

Build artifacts will be created in:  
`build/zephyr/zmk.uf2` or `build/zephyr/zmk.bin`

---

### 4. One-Liner Build (Optional)

Skip the shell step and run everything at once:

```bash
docker-compose run --rm builder \
  west build -s app -b <BOARD> \
    -- \
      -DZMK_CONFIG=/workspaces/zmk-config \
      -DZMK_EXTRA_MODULES=/workspaces/zmk \
      -DSHIELD=<SHIELD>
```

---

## 🗂️ Project Structure

```
.
├── config/                     # Your keymaps, overlays, and config files
├── local-build/
│   └── docker-compose.yml     # Docker setup file
├── boards/shields/            # Optional custom shield definitions
└── zmk/                        # Full clone of ZMK firmware repo
```

---

## 💡 Tips

- Edit files freely in your local `config/` folder—changes are instantly available in the container.
- Artifacts appear in the `build/zephyr/` folder by default.
- Run `west build -c` to clean between builds if needed.

---

## 🧼 Clean Up

Remove containers:

```bash
docker container prune
```

Remove unused images:

```bash
docker image prune
```

---

## 📚 More Resources

- [ZMK Documentation](https://zmk.dev/docs)
- [ZMK Dev Container Setup](https://zmk.dev/docs/development/local-toolchain/setup/container)
