#!/bin/bash
set -e

echo "🛠  Setting up local ZMK build environment..."

# Paths
HOST_CONFIG_MOUNT=/workspaces/zmk-config
CONFIG_PATH=/tmp/zmk-config

HOST_BOARDS_MOUNT=/workspaces/zmk-boards
BOARDS_PATH="${CONFIG_PATH}/boards"
SHIELDS_PATH="${BOARDS_PATH}/shields"

HOST_ZEPHYR_MOUNT=/workspaces/zephyr

HOST_SCRIPTS_MOUNT=/workspaces/zmk-scripts

KEYMAP_SOURCE_DIR=/tmp/keymaps

echo "📁 Copying config: $HOST_CONFIG_MOUNT -> $CONFIG_PATH"
cp -r "$HOST_CONFIG_MOUNT" "$CONFIG_PATH"

echo "📁 Copying board definitions: $HOST_BOARDS_MOUNT -> $BOARDS_PATH"
cp -r "$HOST_BOARDS_MOUNT" "$BOARDS_PATH"

echo "📁 Copying zephyr module: $HOST_ZEPHYR_MOUNT -> $CONFIG_PATH"
cp -r "/workspaces/zephyr" "${CONFIG_PATH}"

# Add keymaps
python3 "${HOST_SCRIPTS_MOUNT}/convert_keymap.py" -c q2c --in-path "${CONFIG_PATH}/charybdis.keymap"
python3 "${HOST_SCRIPTS_MOUNT}/convert_keymap.py" -c q2g --in-path "${CONFIG_PATH}/charybdis.keymap"

# Move keymaps to a tmp directory
echo "📁 Moving keymap files: ${CONFIG_PATH}/*.keymap -> ${KEYMAP_SOURCE_DIR}"
mkdir -p "${KEYMAP_SOURCE_DIR}"
mv ${CONFIG_PATH}/*.keymap "${KEYMAP_SOURCE_DIR}"

if [ ! -d "$SHIELDS_PATH" ]; then
  echo "❌ ERROR: Shields directory does not exist: $SHIELDS_PATH"
  exit 1
fi

# Initialize west environment
cd /workspaces/zmk
if [ ! -d ".west" ]; then
  echo "🔄 Initializing west workspace..."
  west init -l app
else
  echo "🔄 West workspace already initialized — skipping init"
fi

echo "🔄 Updating west modules..."
west update
echo "🔄 Exporting west environment..."
west zephyr-export

# # Set up PMW3610 Driver
# echo "🔄 Setting up PMW3610 driver..."
# git clone https://github.com/badjeff/zmk-pmw3610-driver.git /tmp/pmw3610-driver


# Build matrix based on keymaps and shields
cd /workspaces/zmk
BOARD="nice_nano_v2"
KEYMAPS=($(find ${KEYMAP_SOURCE_DIR} -maxdepth 1 -name "*.keymap" -exec basename {} .keymap \;))
SHIELDS=($(find ${SHIELDS_PATH} -mindepth 1 -maxdepth 1 -type d -exec basename {} \;))

# apt update && apt install -y tree # TODO - DELETE ME

for SH in "${SHIELDS[@]}"; do
  for KM in "${KEYMAPS[@]}"; do
    echo "📄 Building keymap $KM for shield $SH"
    BUILD_DIR=$(mktemp -d)

    # copy the keymap to the shield root
    cp "/${KEYMAP_SOURCE_DIR}/${KM}.keymap" "$CONFIG_PATH/${SH}.keymap"

    # copy config files to shield folder for DTS preprocessor (#include files)
    cp ${CONFIG_PATH}/*.dtsi    ${SHIELDS_PATH}/$SH/
    cp ${CONFIG_PATH}/*.yml     ${SHIELDS_PATH}/$SH/

    # tree "${CONFIG_PATH}" # TODO - DELETE ME

    # build the firmware ulsing west
    west build -s app \
      -d "$BUILD_DIR" \
      -b nice_nano_v2 \
      -- \
        -DSHIELD="${SH}" \
        -DZMK_CONFIG=/tmp/zmk-config \
        -DZMK_EXTRA_MODULES=/tmp/zmk-config \
        -DDTC_INCLUDE_DIRS=/tmp/zmk-config \
        -DDTS_EXTRA_CPPFLAGS="-I/tmp/zmk-config -I/tmp/pmw3610-driver"

    # copy build artifacts to the host
    cp "$BUILD_DIR/zephyr/zmk.uf2" "/workspaces/zmk-firmwares/${SH}-${KM}.uf2"
  done
done

echo "✅ All matrix builds complete."

# Hand off to the container's main process
exec "$@"
