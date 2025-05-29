#!/usr/bin/env bash
# build_zmk_locally.sh - Build ZMK firmware locally based on discovered shields and keymaps

set -euo pipefail

# --- CONFIGURABLE SETTINGS ---
REPO_ROOT="${REPO_ROOT:-$PWD}"                   # path to original repo root
SHIELD_PATH="${SHIELD_PATH:-boards/shields}"     # where shield folders live relative to repo root
CONFIG_PATH="${CONFIG_PATH:-config}"              # where source keymaps/config live
FALLBACK_BINARY="${FALLBACK_BINARY:-bin}"         # fallback firmware extension
SCRIPT_PATH="$REPO_ROOT/scripts/convert_keymap.py"
BUILD_REPO="$REPO_ROOT"
BUILD_REPO="$REPO_ROOT"

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
echo "🔍 Discovering shields in sandbox: $BUILD_REPO/$SHIELD_PATH"
mapfile -t shields < <(
  find "$BUILD_REPO/$SHIELD_PATH" -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
)

# Display discovered shields
if [ ${#shields[@]} -gt 0 ]; then
  echo "📋 Discovered shields:"
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
  echo "📋 Discovered keymaps:" # Using the same clipboard emoji as shields
  for k in "${keymaps[@]}"; do echo "  - $k"; done
else
  echo "⚠️ No keymaps found in $KEYMAP_TEMP" # Adjusting the warning message
fi

# Set up PMW3610 Driver
echo "🔄 Setting up PMW3610 driver..."
git clone https://github.com/badjeff/zmk-pmw3610-driver.git /tmp/pmw3610-driver

# Clear previous firmwares
rm -rf /workspaces/zmk-firmwares/*

echo "🔄 Starting build loop for each shield × keymap"

for shield in "${shields[@]}"; do
  echo "🏗️  Setting up sandbox for shield: $shield"
  WORKSPACE_COPY=$(mktemp -d)
  cp -r "$REPO_ROOT/." "$WORKSPACE_COPY/"
  BUILD_REPO="$WORKSPACE_COPY"
  cd "$BUILD_REPO"

  # Always include the sandbox as extra_module so custom shields are found
  ZMK_LOAD_ARG="-DZMK_EXTRA_MODULES=$BUILD_REPO;/tmp/pmw3610-driver"

  # Determine module mode and set BASE_DIR
  if [ -f zmk/module.yml ]; then
    BASE_DIR="${TMPDIR:-/tmp}/zmk-config"
    mkdir -p "$BASE_DIR/$CONFIG_PATH"
    cp -R "$REPO_ROOT/$CONFIG_PATH/"* "$BASE_DIR/$CONFIG_PATH/"
  else
    BASE_DIR="$BUILD_REPO"
  fi

  # Copy the main repo's .west and modules directories to sandbox—no west init/update/export per build
  if [ -d "$BUILD_REPO/zmk/.west" ]; then rm -rf "$BUILD_REPO/zmk/.west"; fi
  if [ -d "$REPO_ROOT/zmk/.west" ]; then cp -r "$REPO_ROOT/zmk/.west" "$BUILD_REPO/zmk/.west"; fi
  if [ -d "$BUILD_REPO/zmk/modules" ]; then rm -rf "$BUILD_REPO/zmk/modules"; fi
  if [ -d "$REPO_ROOT/zmk/modules" ]; then cp -r "$REPO_ROOT/zmk/modules" "$BUILD_REPO/zmk/modules"; fi

  # Install only the custom shield into the ZMK module’s shields directory
echo "📂 Installing custom shield into ZMK module"
ZMK_SHIELDS_DIR="$BUILD_REPO/zmk/app/boards/shields"
rm -rf "$ZMK_SHIELDS_DIR"/*
mv "$BUILD_REPO/$SHIELD_PATH/$shield" "$ZMK_SHIELDS_DIR/"

# Ensure charybdis-layouts.dtsi is in the shield directory for overlay includes
LAYOUTS_SRC="$BASE_DIR/$CONFIG_PATH/charybdis-layouts.dtsi"
if [ -f "$LAYOUTS_SRC" ]; then
  cp "$LAYOUTS_SRC" "$ZMK_SHIELDS_DIR/$shield/charybdis-layouts.dtsi"
fi

# Initialize and export west workspace inside the zmk module folder
  cd "$BUILD_REPO/zmk"
  if [ ! -d ".west" ]; then
    echo "🔄 Initializing west workspace in sandbox (zmk/.west)..."
    west init -l "$BASE_DIR/$CONFIG_PATH"
  else
    echo "🔄 West workspace already initialized in sandbox — skipping init"
  fi
  echo "🔄 Updating west modules..."
  west update
  echo "🔄 Exporting west environment..."
  west zephyr-export

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
      echo "⚙️  Building: shield=$target, keymap=$keymap, board=$board"

      BUILD_DIR=$(mktemp -d)
      echo "  → Build dir: $BUILD_DIR"

      cp "$KEYMAP_TEMP/${keymap}.keymap" \
         "$BASE_DIR/$CONFIG_PATH/charybdis.keymap"

      west build --pristine -s app \
        -d "$BUILD_DIR" \
        -b "$board" \
        -S studio-rpc-usb-uart \
        -- \
          -DZMK_CONFIG="$BASE_DIR/$CONFIG_PATH" \
          -DSHIELD="$target" $ZMK_LOAD_ARG
      
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
      FIRMWARES_DIR="/workspaces/zmk-firmwares/${keymap}"
      mkdir -p "$FIRMWARES_DIR"
      chmod 777 "$FIRMWARES_DIR"
      DEST="$FIRMWARES_DIR/${target}.${ARTIFACT_EXT}"
      echo "🚚 Publishing $ARTIFACT_SRC → $DEST"
      cp "$ARTIFACT_SRC" "$DEST"
      chmod 666 "$DEST"
    done
  done
done

echo "🏁 All builds completed."












































# config_path="config"
# WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}"
# HOST_SCRIPTS_MOUNT=/workspaces/zmk-scripts

# # Create build directory
# build_dir=$(mktemp -d)

# # detect if we’re building this repo as its own Zephyr module
# if [[ -f zephyr/module.yml ]]; then
#   # pass “this dir” into CMake so it picks up your module.yml
#   zmk_load_arg="-DZMK_EXTRA_MODULES=$(pwd)"
#   # create a tmp config dir for overlays/etc
#   base_dir="/tmp/zmk-config"
#   mkdir -p "$base_dir"
# else
#   # otherwise just use the repo root
#   base_dir="$(WORKSPACE_ROOT)"
# fi

# echo "Using base_dir=$base_dir"
# echo "Extra CMake args: $zmk_load_arg"

# if [ -n "${snippet}" ]; then
#   extra_west_args="-S \"${snippet}\""
# fi

# # Generate and store keymaps
# keymap_path="boards/shields/charybdis/keymaps"
# cd "${WORKSPACE_ROOT}" || exit 1
# python3 "${HOST_SCRIPTS_MOUNT}/convert_keymap.py" -c q2c --in-path "${WORKSPACE_ROOT}/config/charybdis.keymap"
# python3 "${HOST_SCRIPTS_MOUNT}/convert_keymap.py" -c q2g --in-path "${WORKSPACE_ROOT}/config/charybdis.keymap"
# mv charybdis.keymap qwerty.keymap
# mv ./*.keymap "${WORKSPACE_ROOT}/${keymap_path}/"
# ls -lR "${WORKSPACE_ROOT}/${keymap_path}/"

# # Initialize west environment
# cd /workspaces/zmk
# if [ ! -d ".west" ]; then
#   echo "🔄 Initializing west workspace..."
#   west init -l app
# else
#   echo "🔄 West workspace already initialized — skipping init"
# fi

# echo "🔄 Updating west modules..."
# west update
# echo "🔄 Exporting west environment..."
# west zephyr-export

# # Set up PMW3610 Driver
# echo "🔄 Setting up PMW3610 driver..."
# git clone https://github.com/badjeff/zmk-pmw3610-driver.git /tmp/pmw3610-driver
# echo ""

# # Copy files to isolated temporary directory for building





























# # Build matrix based on keymaps and shields
# cd "${WORKSPACE_ROOT}"
# BOARD="nice_nano_v2"
# KEYMAPS=($(find ${keymap_path} -maxdepth 1 -name "*.keymap" -exec basename {} .keymap \;))
# SHIELDS=($(find ${SHIELDS_PATH} -mindepth 1 -maxdepth 1 -type d -exec basename {} \;))









# # Copy config files to isolated temporary directory
# config_dest="$base_dir/$config_path"
# echo "📦 Copying config files from $WORKSPACE_ROOT/$config_path to $config_dest"
# mkdir -p "$config_dest"
# cp -R "$WORKSPACE_ROOT/$config_path/"* "$config_dest/"

# echo "✅ Config files now available in $config_dest:"
# ls -l "$config_dest"



# # Copy keymap & physical layouts
# if [ "$shield" != "settings_reset" ]; then
#   echo "📦 Moving physical layout for shield: $shield (format: $format)"
#   mv -v \
#     "$config_dest/charybdis-layouts.dtsi" \
#     "$base_dir/boards/shields/charybdis-$format/"
# fi








# # base_config_path  config_dest
# # GITHUB_WORKSPACE  WORKSPACE_ROOT





# HOST_CONFIG_MOUNT=/workspaces/zmk-config
# CONFIG_PATH=/tmp/zmk-config

# HOST_BOARDS_MOUNT=/workspaces/zmk-boards
# BOARDS_PATH="${CONFIG_PATH}/boards"
# # SHIELDS_PATH="${BOARDS_PATH}/shields"
# SHIELDS_PATH="${CONFIG_PATH}/shields"

# HOST_ZEPHYR_MOUNT=/workspaces/zephyr

# HOST_SCRIPTS_MOUNT=/workspaces/zmk-scripts

# KEYMAP_SOURCE_DIR=/tmp/keymaps

# echo "📁 Copying config: $HOST_CONFIG_MOUNT -> $CONFIG_PATH"
# cp -r "$HOST_CONFIG_MOUNT" "$CONFIG_PATH"

# # echo "📁 Copying board definitions: $HOST_BOARDS_MOUNT -> $BOARDS_PATH"
# # cp -r "$HOST_BOARDS_MOUNT" "$BOARDS_PATH"

# echo "📁 Copying shield definitions: $SHIELDS_PATH -> $CONFIG_PATH"
# cp -r "$HOST_BOARDS_MOUNT" "$SHIELDS_PATH"

# echo "📁 Copying zephyr module: $HOST_ZEPHYR_MOUNT -> $CONFIG_PATH"
# cp -r "/workspaces/zephyr" "${CONFIG_PATH}"


# # Move keymaps to a tmp directory
# echo "📁 Moving keymap files: ${CONFIG_PATH}/*.keymap -> ${KEYMAP_SOURCE_DIR}"
# mkdir -p "${KEYMAP_SOURCE_DIR}"
# mv ${CONFIG_PATH}/*.keymap "${KEYMAP_SOURCE_DIR}"

# if [ ! -d "$SHIELDS_PATH" ]; then
#   echo "❌ ERROR: Shields directory does not exist: $SHIELDS_PATH"
#   exit 1
# fi









# apt update && apt install -y tree # TODO - DELETE ME

# for SH in "${SHIELDS[@]}"; do
#   for KM in "${KEYMAPS[@]}"; do
#     echo "📄 Building keymap $KM for shield $SH"
#     BUILD_DIR=$(mktemp -d)

#     # copy the keymap to the shield root
#     cp "/${KEYMAP_SOURCE_DIR}/${KM}.keymap" "$CONFIG_PATH/${SH}.keymap"

#     # copy config files to shield folder for DTS preprocessor (#include files)
#     cp ${CONFIG_PATH}/*.dtsi    ${SHIELDS_PATH}/$SH/
#     cp ${CONFIG_PATH}/*.yml     ${SHIELDS_PATH}/$SH/
#     cp ${CONFIG_PATH}/charybdis.json     ${SHIELDS_PATH}/$SH/info.json

#     tree "${CONFIG_PATH}" # TODO - DELETE ME

#     # build the firmware ulsing west
#     west build -s app \
#       -d "$BUILD_DIR" \
#       -b nice_nano_v2 \
#       -- \
#         -DSHIELD=charybdis_dongle_right \
#         -DZMK_CONFIG=/tmp/zmk-config \
#         -DZMK_EXTRA_MODULES="/tmp/zmk-config;/tmp/pmw3610-driver" \
#         -DDTC_INCLUDE_DIRS="/tmp/zmk-config" \
#         -DDTS_EXTRA_CPPFLAGS="-I/tmp/zmk-config -I/tmp/pmw3610-driver" \
#         -DSHIELD_ROOT=/tmp/zmk-config/boards/shields
#         # -DBOARD_ROOT=/tmp/zmk-config/boards


#     # copy build artifacts to the host
#     cp "$BUILD_DIR/zephyr/zmk.uf2" "/workspaces/zmk-firmwares/${SH}-${KM}.uf2"
#   done
# done

# echo "✅ All matrix builds complete."

# # Hand off to the container's main process
# exec "$@"
