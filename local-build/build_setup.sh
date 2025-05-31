#!/usr/bin/env bash
# build_zmk_locally.sh - Build ZMK firmware locally based on discovered shields and keymaps

set -euo pipefail
start_time=$(date +%s)

# --- CONFIGURABLE SETTINGS ---
REPO_ROOT="${REPO_ROOT:-$PWD}"                   # path to original repo root
SHIELD_PATH="${SHIELD_PATH:-boards/shields}"     # where shield folders live relative to repo root
CONFIG_PATH="${CONFIG_PATH:-config}"              # where source keymaps/config live
FALLBACK_BINARY="${FALLBACK_BINARY:-bin}"         # fallback firmware extension
SCRIPT_PATH="$REPO_ROOT/scripts/convert_keymap.py"

# Prepare temporary keymap directory
echo "📁 Copying source keymaps from $CONFIG_PATH to temporary directory"
KEYMAP_TEMP="/tmp/keymaps"
rm -rf "$KEYMAP_TEMP" && mkdir -p "$KEYMAP_TEMP"
cp "$REPO_ROOT/$CONFIG_PATH"/*.keymap "$KEYMAP_TEMP/"

# Generate additional keymaps
## Comment these lines out to prevent building different keymaps
echo "🔧 Generating additional keymaps"
python3 "$SCRIPT_PATH" -c q2c --in-path "$KEYMAP_TEMP/charybdis.keymap"
python3 "$SCRIPT_PATH" -c q2g --in-path "$KEYMAP_TEMP/charybdis.keymap"
mv "$KEYMAP_TEMP/charybdis.keymap" "$KEYMAP_TEMP/qwerty.keymap"

# Discover shields
echo "🔍 Discovering shields in sandbox: $REPO_ROOT/$SHIELD_PATH"
mapfile -t shields < <(
  find "$REPO_ROOT/$SHIELD_PATH" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
)

# Display discovered shields
if [ ${#shields[@]} -gt 0 ]; then
  for s in "${shields[@]}"; do echo "  - $s"; done
else
  echo "⚠️ No shields found in $REPO_ROOT/$SHIELD_PATH"
fi

# Discover keymaps
echo "🔍 Discovering keymaps in: $KEYMAP_TEMP"
mapfile -t keymaps < <(
  find "$KEYMAP_TEMP" -maxdepth 1 -type f -name '*.keymap' -exec basename {} .keymap \;
)

# Display discovered keymaps
if [ ${#keymaps[@]} -gt 0 ]; then
  for k in "${keymaps[@]}"; do echo "  - $k"; done
else
  echo "⚠️ No keymaps found in $KEYMAP_TEMP"
fi

# Clear previous firmwares
rm -rf /workspaces/zmk-firmwares/*

# --- PMW3610 Driver Setup ---
# Clone PMW3610 Driver
echo "Setting up PMW3610 driver..."
git clone https://github.com/badjeff/zmk-pmw3610-driver.git /tmp/pmw3610-driver

# Register the pixart vendor prefix in the Devicetree bindings so Zephyr doesn't complain
echo "🛠️  Patching pmw3610-driver to register the pixart vendor..."
printf "pixart\tPixArt Imaging, Inc.\n" >> /tmp/pmw3610-driver/dts/bindings/vendor-prefixes.txt

# Patch the CMakeLists to prevent 'No SOURCES given to Zephyr library' warning
echo "🛠️  Patching pmw3610-driver CMakeLists.txt to avoid empty Zephyr target warning..."
cat > /tmp/pmw3610-driver/CMakeLists.txt << 'EOF'
if(CONFIG_PMW3610)
  zephyr_library()
  zephyr_library_sources(src/pmw3610.c)
  zephyr_include_directories(${APPLICATION_SOURCE_DIR}/include)
endif()
EOF


# --- SANDBOX SETUP FUNCTION ---
setup_sandbox() {
  local shield="$1"

  # Copy in zmk base repo to the sandbox
  echo ""
  echo "🏖️  Setting up sandbox for shield: $shield"
  WORKSPACE_COPY=$(mktemp -d)
  cp -r "$REPO_ROOT/." "$WORKSPACE_COPY/"
  BUILD_REPO="$WORKSPACE_COPY"
  cd "$BUILD_REPO"

  # Determine module mode, set BASE_DIR, copy user config
  if [ -f zmk/module.yml ]; then
      if [ "$shield" != "settings_reset" ]; then
        BASE_DIR="${TMPDIR:-/tmp}/zmk-config"
        mkdir -p "$BASE_DIR/$CONFIG_PATH"
        cp -R "$REPO_ROOT/$CONFIG_PATH/"* "$BASE_DIR/$CONFIG_PATH/"
      else
        BASE_DIR="$BUILD_REPO"  # use sandbox root for clean build
      fi
    else
      BASE_DIR="$BUILD_REPO"
  fi

  # Copy the main repo's .west and modules directories to sandbox—no west init/update/export per build
  if [ -d "$BUILD_REPO/zmk/.west" ]; then rm -rf "$BUILD_REPO/zmk/.west"; fi
  if [ -d "$REPO_ROOT/zmk/.west" ]; then cp -r "$REPO_ROOT/zmk/.west" "$BUILD_REPO/zmk/.west"; fi
  if [ -d "$BUILD_REPO/zmk/modules" ]; then rm -rf "$BUILD_REPO/zmk/modules"; fi
  if [ -d "$REPO_ROOT/zmk/modules" ]; then cp -r "$REPO_ROOT/zmk/modules" "$BUILD_REPO/zmk/modules"; fi

 # Initialize and export west workspace inside the zmk module folder
  cd "$BUILD_REPO/zmk"
  if [ ! -d ".west" ]; then
    echo " → Initializing west workspace in sandbox (zmk/.west)..."
    west init -l "$BASE_DIR/$CONFIG_PATH"
  else
    echo " → West workspace already initialized in sandbox — skipping init"
  fi
  echo " → Updating west modules..."
  west update
  echo " → Exporting west environment..."
  west zephyr-export
}


# --- BUILD LOOP FOR EACH SHIELD x KEYMAP ---
echo "Starting build loop for each shield × keymap"

for shield in "${shields[@]}"; do

  # Set up Sandbox
  setup_sandbox "$shield"
  cd "$BUILD_REPO/zmk"

  # Always include the sandbox as extra_module so custom shields are found
  ZMK_LOAD_ARG="-DZMK_EXTRA_MODULES=$BUILD_REPO;/tmp/pmw3610-driver"

  # Install only the custom shield into the ZMK module’s shields directory
  printf "⚙️  %s\n" "→ Installing custom shield ($shield) into ZMK module"
  ZMK_SHIELDS_DIR="$BUILD_REPO/zmk/app/boards/shields"
  rm -rf "$ZMK_SHIELDS_DIR"/*
  mv "$BUILD_REPO/$SHIELD_PATH/$shield" "$ZMK_SHIELDS_DIR/"

  # Ensure charybdis-layouts.dtsi is in the shield directory for overlay includes
  LAYOUTS_SRC="$BASE_DIR/$CONFIG_PATH/charybdis-layouts.dtsi"
  if [ -f "$LAYOUTS_SRC" ]; then
    cp "$LAYOUTS_SRC" "$ZMK_SHIELDS_DIR/$shield/charybdis-layouts.dtsi"
  fi

  # Ensure charybdis_pmw3610.dtsi is in the shield directory for overlay includes
  LAYOUTS_SRC="$BASE_DIR/$CONFIG_PATH/charybdis_pmw3610.dtsi"
  if [ -f "$LAYOUTS_SRC" ]; then
    cp "$LAYOUTS_SRC" "$ZMK_SHIELDS_DIR/$shield/charybdis_pmw3610.dtsi"
  fi

  # Find all shield targets (e.g. charybdis_right, charybdis_left) in this shield folder
  mapfile -t shield_targets < <(
    find "$ZMK_SHIELDS_DIR/$shield" -maxdepth 1 -type f -name "charybdis_*.overlay" -exec basename {} .overlay \;
  )
  if [ ${#shield_targets[@]} -eq 0 ]; then
    echo "⚠️  No *_left or *_right overlays found in $ZMK_SHIELDS_DIR/$shield, skipping."
    continue
  fi

  for target in "${shield_targets[@]}"; do
    for keymap in "${keymaps[@]}"; do
      board="nice_nano_v2"
      artifact_name="${target}-${keymap}-${board}-zmk"
      BUILD_DIR=$(mktemp -d)
      printf "🗂  %s\n" "→ Build dir: $BUILD_DIR"
      printf "🛡  %s\n" "→ Building: shield=$shield, target=$target keymap=$keymap, board=$board"

      # Turn on ZMK Studio for right-side BT builds only
      if [[ "$shield" == *bt* && "$target" == *right ]]; then
        STUDIO_SNIPPET="-S studio-rpc-usb-uart"
      else
        STUDIO_SNIPPET=""
      fi

      # Load in the keymap
      cp "$KEYMAP_TEMP/${keymap}.keymap" \
         "$BASE_DIR/$CONFIG_PATH/charybdis.keymap"

      west build --pristine -s app \
        -d "$BUILD_DIR" \
        -b "$board" \
        $STUDIO_SNIPPET \
        -- \
          -DZMK_CONFIG="$BASE_DIR/$CONFIG_PATH" \
          -DSHIELD="$target" $ZMK_LOAD_ARG
          # -DCMAKE_VERBOSE_MAKEFILE=ON # verbose logging
      echo ""
      
      # Find the built firmware (prefer .uf2, else fallback)
      ARTIFACT_SRC=""
      if [ -f "$BUILD_DIR/zephyr/zmk.uf2" ]; then
        ARTIFACT_SRC="$BUILD_DIR/zephyr/zmk.uf2"
        ARTIFACT_EXT="uf2"
      elif [ -f "$BUILD_DIR/zephyr/zmk.${FALLBACK_BINARY}" ]; then
        ARTIFACT_SRC="$BUILD_DIR/zephyr/zmk.${FALLBACK_BINARY}"
        ARTIFACT_EXT="$FALLBACK_BINARY"
      else
        echo "❌ No firmware artifact found for $artifact_name"
        continue
      fi

      # Create keymap-specific directory and use target as the filename
      FIRMWARES_FORMAT_DIR="/workspaces/zmk-firmwares/${shield}"
      FIRMWARES_DIR="${FIRMWARES_FORMAT_DIR}/${keymap}"

      # If format directory doesn't exist, create and chmod it
      if [ ! -d "$FIRMWARES_FORMAT_DIR" ]; then
        mkdir -p "$FIRMWARES_FORMAT_DIR"
        chmod 777 "$FIRMWARES_FORMAT_DIR"
      fi

      # If keymap directory doesn't exist, create and chmod it
      if [ ! -d "$FIRMWARES_DIR" ]; then
        mkdir -p "$FIRMWARES_DIR"
        chmod 777 "$FIRMWARES_DIR"
      fi

      DEST="$FIRMWARES_DIR/${target}.${ARTIFACT_EXT}"
      echo "Publishing $ARTIFACT_SRC → $DEST"
      cp "$ARTIFACT_SRC" "$DEST"
      chmod 666 "$DEST"
      echo ""
    done
  done
  # Clean up sandbox
  echo "Cleaning up sandbox..."
  rm -rf $WORKSPACE_COPY
done


# --- BUILD RESET FIRMWARE ---
setup_sandbox "settings_reset"
cd "$BUILD_REPO/zmk"
RESET_BOARD="nice_nano_v2"
BUILD_DIR=$(mktemp -d)
FIRM_PATH="/workspaces/zmk-firmwares/settings_reset.uf2"
printf "🗂  %s\n" "→ Build dir: $BUILD_DIR"
printf "🔧  %s\n" "→ Building settings_reset firmware..."

west build --pristine -s app \
  -d "$BUILD_DIR" \
  -b "$RESET_BOARD" \
  -- \
    -DSHIELD=settings_reset \
    -DCONFIG_NRF_STORE_REBOOT_TYPE_GPREGRET=n \
    > build.log 2>&1 # ignore all the keymap warnings

cp "$BUILD_DIR/zephyr/zmk.uf2" "$FIRM_PATH"
chmod 666 "$FIRM_PATH"


# --- CALCULATE EXECUTION TIME ---
end_time=$(date +%s)
elapsed=$(( end_time - start_time ))
minutes=$(( elapsed / 60 ))
seconds=$(( elapsed % 60 ))
echo "🏁 All builds completed in ${minutes} m ${seconds} s."