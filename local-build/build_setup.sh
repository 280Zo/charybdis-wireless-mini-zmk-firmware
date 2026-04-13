#!/usr/bin/env bash
# build_zmk_locally.sh - Build ZMK firmware locally based on the matrix created from build.yaml

set -euo pipefail
START_TIME=$(date +%s)

# --- CONFIGURABLE SETTINGS ---
ENABLE_USB_LOGGING="false"                         # Set to "true" to enable USB logging in the firmware
REPO_ROOT="${REPO_ROOT:-$PWD}"                     # path to original repo root
SHIELD_PATH="${SHIELD_PATH:-boards/shields}"       # where shield folders live relative to repo root
CONFIG_PATH="${CONFIG_PATH:-config}"               # where configs live
FALLBACK_BINARY="${FALLBACK_BINARY:-bin}"          # fallback firmware extension

# --- ZMK WORKSPACE ---
echo ""
echo "=== SETUP ZMK WORKSPACE ==="

# Only init if not already initialized (i.e., .west folder doesn't exist)
if [ ! -d ".west" ]; then
    echo "    Initializing west workspace..."
    west init -l config
fi

# Update to fetch all modules and dependencies
echo "Updating west modules..."
west update

# Set environment variables in the current shell
echo "Preparing Zephyr build environment..."
west zephyr-export

# Set location for local binaries
LOCAL_BIN_DIR="$REPO_ROOT/local-build"
mkdir -p "$LOCAL_BIN_DIR"

# Add LOCAL_BIN_DIR to PATH if not already there
if [[ ":$PATH:" != *":$LOCAL_BIN_DIR:"* ]]; then
  PATH="$LOCAL_BIN_DIR:$PATH"
fi

# Install yq (downloads Mike Farah's Go-based yq) for YAML processing
if [ ! -f "$LOCAL_BIN_DIR/yq" ]; then
  echo "Installing yq..."
  curl -fsSL https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o "$LOCAL_BIN_DIR/yq"
  chmod +x "$LOCAL_BIN_DIR/yq"
else
  echo "yq already installed."
fi

# Install jq binary for JSON processing
if [ ! -f "$LOCAL_BIN_DIR/jq" ]; then
  echo "Installing jq..."
  curl -fsSL https://github.com/stedolan/jq/releases/latest/download/jq-linux64 -o "$LOCAL_BIN_DIR/jq"
  chmod +x "$LOCAL_BIN_DIR/jq"
else
  echo "jq already installed."
fi

# Set permissions so users can delete them in their own environment
echo "Setting permissions on ZMK resources..."
chmod -R 777 .west zmk zephyr modules zmk-pmw3610-driver prospector-zmk-module

# # Debug: confirm checkout
# echo "    West workspace ready. Project structure:"
# west list

# Parse build entries from build.yaml
mapfile -t build_entries < <(
  yq eval -o=json '.include // []' "$REPO_ROOT/build.yaml" | jq -c '.[]'
)

if [ ${#build_entries[@]} -eq 0 ]; then
  echo "[WARN] No build entries defined in build.yaml"
  exit 0
fi


# --- SANDBOX SETUP FUNCTION ---
setup_sandbox() {
  local shield="$1"

  # Copy in zmk base repo to the sandbox
  echo ""
  echo "=== PREPARING SANDBOX ==="

  SANDBOX_ROOT=$(mktemp -d)
  echo "Copying repository into sandbox root"

  # Copy in all files from the original repo to the sandbox for modules and imports
  cp -r "$REPO_ROOT/." "$SANDBOX_ROOT/"

  # Copy all configs to the sandboxed zmk app path
  # This will allow #include directives to be the same as they are in the repo
  printf 'Installing configs\n'
  NEW_CONFIG_PATH="$SANDBOX_ROOT/zmk/app/config"
  rm -rf "$NEW_CONFIG_PATH"
  mkdir -p "$NEW_CONFIG_PATH"
  cp -r "$SANDBOX_ROOT/$CONFIG_PATH"/* "$NEW_CONFIG_PATH/"

  # Copy charybdis/ conf files to top-level config location so ZMK finds them.
  for f in "$SANDBOX_ROOT/$CONFIG_PATH/charybdis/"*.conf; do
    [ -f "$f" ] && cp "$f" "$NEW_CONFIG_PATH/$(basename "$f")"
  done

  # Custom shields are picked up via the boards/ module (ZMK_EXTRA_MODULES).
  # No manual copy needed; point ZMK_SHIELDS_DIR at their source location.
  ZMK_SHIELDS_DIR="$SANDBOX_ROOT/boards/shields"

  if [[ "$shield" == "settings_reset" ]]; then
    echo "Using upstream settings_reset shield"

    # Patch the settings_reset overlay mock kscan with a single entry so GCC stops warning about zero length.
    reset_overlay="$SANDBOX_ROOT/zmk/app/boards/shields/settings_reset/settings_reset.overlay"
    sed -i 's/rows = <0>;/rows = <1>;/' "$reset_overlay"
    sed -i 's/events = <>;/events = <0>;/' "$reset_overlay"
  fi

  cd "$SANDBOX_ROOT"
}

# Clear previous firmwares
rm -rf /workspaces/zmk/firmwares/*


# --- BUILD FIRMWARE FUNCTION ---
build_firmware() {
  local shield="$1"
  local target="$2"
  local board="$3"
  local keymap="${4:-}"

  local build_dir
  build_dir=$(mktemp -d)

  printf '\n=== BUILDING FIRMWARE ===\n'
  printf 'Build Context:\n'
  printf '  Shield : %s\n' "$shield"
  printf '  Target : %s\n' "$target"
  if [[ -n "$keymap" ]]; then
    printf '  Keymap : %s\n' "$keymap"
  fi
  printf '  Board  : %s\n' "$board"
  printf "\n"

  printf 'Build Directory:\n'
  printf '  %s\n' "$build_dir"

  # Apply studio-rpc-usb-uart to USB central shields only.
  # charybdis_right_bt is the central in BT split mode.
  # charybdis_dongle is the central in dongle mode.
  # Skip when USB logging is enabled since both use USB CDC and conflict.
  local extra_snippet=""
  if [[ "$ENABLE_USB_LOGGING" != "true" ]] && [[ "$target" == "charybdis_right_bt" || "$target" == "charybdis_dongle" ]]; then
    extra_snippet="-S studio-rpc-usb-uart"
  fi

  # Enable USB logging if specified at the top of this script
  local usb_logging_snippet=""
  if [[ "$ENABLE_USB_LOGGING" == "true" ]]; then
    usb_logging_snippet="-S zmk-usb-logging"
  fi

  # Pass the boards/ module so ZMK can discover the custom shields,
  # and the pmw3610 driver module.
  local zmk_load_arg="-DZMK_EXTRA_MODULES=$SANDBOX_ROOT/boards;$SANDBOX_ROOT/zmk-pmw3610-driver;$SANDBOX_ROOT/prospector-zmk-module"
  local extra_conf_arg=()
  local extra_dtc_overlay_arg=()

  if [ ${#entry_extra_conf_files[@]} -gt 0 ]; then
    local extra_conf_paths=()
    local conf_file
    for conf_file in "${entry_extra_conf_files[@]}"; do
      extra_conf_paths+=("$NEW_CONFIG_PATH/$conf_file")
    done
    extra_conf_arg=("-DEXTRA_CONF_FILE=$(IFS=';'; echo "${extra_conf_paths[*]}")")
  fi

  if [ ${#entry_extra_dtc_overlay_files[@]} -gt 0 ]; then
    local extra_dtc_overlay_paths=()
    local overlay_file
    for overlay_file in "${entry_extra_dtc_overlay_files[@]}"; do
      extra_dtc_overlay_paths+=("$NEW_CONFIG_PATH/$overlay_file")
    done
    extra_dtc_overlay_arg=("-DEXTRA_DTC_OVERLAY_FILE=$(IFS=';'; echo "${extra_dtc_overlay_paths[*]}")")
  fi

  # For stacked shields (space-separated, e.g. "charybdis_dongle prospector_adapter"),
  # -DSHIELD must be the full stacked string. Substitute the discovered target overlay
  # name in place of the primary shield token in case they differ.
  local dshield
  if [[ "$shield" == *" "* ]]; then
    local primary="${shield%% *}"
    dshield="${shield/$primary/$target}"
  else
    dshield="$target"
  fi

  # Run the build
  west build --pristine -s "$SANDBOX_ROOT/zmk/app" \
    -d "$build_dir" \
    -b "$board" \
    $extra_snippet \
    $usb_logging_snippet \
    -- \
      -DZMK_CONFIG="$NEW_CONFIG_PATH" \
      -DSHIELD="$dshield" \
      "${extra_conf_arg[@]}" \
      "${extra_dtc_overlay_arg[@]}" \
      $zmk_load_arg \

  echo ""

  # Determine the artifact type to copy (prefer .uf2, fallback to specified binary type)
  local artifact_src=""
  local artifact_ext=""
  if [ -f "$build_dir/zephyr/zmk.uf2" ]; then
    artifact_src="$build_dir/zephyr/zmk.uf2"
    artifact_ext="uf2"
  elif [ -f "$build_dir/zephyr/zmk.${FALLBACK_BINARY}" ]; then
    artifact_src="$build_dir/zephyr/zmk.${FALLBACK_BINARY}"
    artifact_ext="$FALLBACK_BINARY"
  else
    echo "[WARN] No firmware artifact found for ${target}-${keymap}-${board}"
    return 1
  fi

  echo "=== PUBLISHING ARTIFACT & CLEANING UP ==="
  # Map the entry format to the correct directory name:
  # "bt"                - use charybdis_bt
  # "dongle_standard_nano" - use charybdis_dongle
  # Prospector entries  - use charybdis_dongle_prospector_<board>_<variant>
  # anything else       - just use the original format name
  case "$entry_format" in
    bt)                format_dir="charybdis_bt" ;;
    dongle_standard_nano)   format_dir="charybdis_dongle" ;;
    dongle_prospector_no_sensor|dongle_prospector_nano_no_sensor)
      format_dir="charybdis_dongle_prospector_nice_nanov2_no_sensor"
      ;;
    dongle_prospector_sensor|dongle_prospector_nano_sensor)
      format_dir="charybdis_dongle_prospector_nice_nanov2_sensor"
      ;;
    dongle_prospector_xiao_no_sensor)
      format_dir="charybdis_dongle_prospector_xiao_no_sensor"
      ;;
    dongle_prospector_xiao_sensor)
      format_dir="charybdis_dongle_prospector_xiao_sensor"
      ;;
    *)                 format_dir="$entry_format" ;;
  esac

  # Publish the firmware artifact to the correct directory and set permissions
  local dest
  local firmwares_format_dir

  if [[ "$shield" == "settings_reset" ]]; then
    # Reset firmware goes at top-level (no folder)
    firmwares_dir="/workspaces/zmk/firmwares"
    mkdir -p "$firmwares_dir"
    chmod 777 "$firmwares_dir"
    dest="$firmwares_dir/settings_reset.${artifact_ext}"
  else
    # Normal builds are structured by format/keymap
    local firmwares_format_dir="/workspaces/zmk/firmwares/${format_dir}"
    local dir_suffix="${keymap:-${shield}_no_keymap}"
    firmwares_dir="${firmwares_format_dir}/${dir_suffix}"

    mkdir -p "$firmwares_dir"
    chmod 777 "$firmwares_format_dir" "$firmwares_dir"
    dest="$firmwares_dir/${target}.${artifact_ext}"
  fi
  
  printf 'Source: %s\n' "$artifact_src"
  printf 'Destination: %s\n' "$dest"
  cp "$artifact_src" "$dest"
  chmod 666 "$dest"
}

parse_string_or_array_field() {
  local json_input="$1"
  local field_name="$2"

  jq -r --arg field "$field_name" '
    if has($field) then
      if (.[$field] | type) == "array" then .[$field][] else .[$field] end
    else
      empty
    end
  ' <<<"$json_input"
}

echo "Generating build matrix for each board, shield, and keymap combination in build.yaml..."
for entry_json in "${build_entries[@]}"; do
  # Pull format & snippet values out of the JSON
  entry_format=$(jq -r '.format // .name // "custom"' <<<"$entry_json")
  entry_snippet=$(jq -r '.snippet // ""' <<<"$entry_json")
  mapfile -t entry_extra_conf_files < <(parse_string_or_array_field "$entry_json" "extra_conf_files")
  mapfile -t entry_extra_dtc_overlay_files < <(parse_string_or_array_field "$entry_json" "extra_dtc_overlay_files")
  mapfile -t entry_boards < <(parse_string_or_array_field "$entry_json" "board")

  if [ ${#entry_boards[@]} -eq 0 ]; then
    entry_boards=("nice_nano_v2")
  fi

  mapfile -t entry_keymaps < <(parse_string_or_array_field "$entry_json" "keymap")
  mapfile -t build_items < <(jq -c '.builds[]?' <<<"$entry_json")

  if [ ${#build_items[@]} -eq 0 ]; then
    mapfile -t entry_shields < <(jq -r '
      if has("shield") then
        if (.shield | type) == "array" then .shield[] else .shield end
      elif has("shields") then
        if (.shields | type) == "array" then .shields[] else .shields end
      else
        empty
      end
    ' <<<"$entry_json")

    if [ ${#entry_shields[@]} -eq 0 ]; then
      printf '[WARN] No shields listed for entry: %s\n' "$entry_json"
      continue
    fi

    for shield in "${entry_shields[@]}"; do
      build_items+=("{\"shield\": $(jq -Rn --arg shield "$shield" '$shield')}")
    done
  fi

  for build_json in "${build_items[@]}"; do
    mapfile -t build_boards < <(parse_string_or_array_field "$build_json" "board")
    mapfile -t build_shields < <(jq -r '
      if has("shield") then
        if (.shield | type) == "array" then .shield[] else .shield end
      elif has("shields") then
        if (.shields | type) == "array" then .shields[] else .shields end
      else
        empty
      end
    ' <<<"$build_json")
    mapfile -t build_keymaps < <(parse_string_or_array_field "$build_json" "keymap")
    mapfile -t build_extra_conf_files < <(parse_string_or_array_field "$build_json" "extra_conf_files")
    mapfile -t build_extra_dtc_overlay_files < <(parse_string_or_array_field "$build_json" "extra_dtc_overlay_files")

    if [ ${#build_boards[@]} -eq 0 ]; then
      build_boards=("${entry_boards[@]}")
    fi

    if [ ${#build_shields[@]} -eq 0 ]; then
      printf '[WARN] No shields listed for build item: %s\n' "$build_json"
      continue
    fi

    if [ ${#build_keymaps[@]} -eq 0 ]; then
      build_keymaps=("${entry_keymaps[@]}")
    fi

    entry_extra_conf_files=("${build_extra_conf_files[@]}")
    if [ ${#entry_extra_conf_files[@]} -eq 0 ]; then
      mapfile -t entry_extra_conf_files < <(parse_string_or_array_field "$entry_json" "extra_conf_files")
    fi

    entry_extra_dtc_overlay_files=("${build_extra_dtc_overlay_files[@]}")
    if [ ${#entry_extra_dtc_overlay_files[@]} -eq 0 ]; then
      mapfile -t entry_extra_dtc_overlay_files < <(parse_string_or_array_field "$entry_json" "extra_dtc_overlay_files")
    fi

    for entry_board in "${build_boards[@]}"; do
      for shield in "${build_shields[@]}"; do
      setup_sandbox "$shield"
      cd "$SANDBOX_ROOT/zmk"

      # Discover overlay targets for custom shields.
      # For settings_reset the target name is the shield itself (upstream ZMK shield).
      if [[ "$shield" == "settings_reset" ]]; then
        shield_targets=("settings_reset")
      else
        # For stacked shields (space-separated, e.g. "charybdis_dongle prospector_adapter"),
        # use only the first token for overlay discovery; the full string is passed to -DSHIELD.
        primary_shield="${shield%% *}"
        mapfile -t shield_targets < <(
          find "$ZMK_SHIELDS_DIR/$primary_shield" -maxdepth 1 -type f -name "*.overlay" -exec basename {} .overlay \;
        )
        if [ ${#shield_targets[@]} -eq 0 ]; then
          echo "[WARN] No overlay targets found in $shield"
          rm -rf "$SANDBOX_ROOT"
          continue
        fi
      fi

      for target in "${shield_targets[@]}"; do
        if [[ "$shield" == "settings_reset" ]]; then
          # Build once without a keymap for settings_reset shield
          build_firmware "$shield" "$target" "$entry_board"
        else
          if [ ${#build_keymaps[@]} -eq 0 ]; then
            printf '[WARN] No keymap specified for build item: %s\n' "$build_json"
            continue
          fi
          # Loop over every keymap
          for entry_keymap in "${build_keymaps[@]}"; do
            keymap_path="$NEW_CONFIG_PATH/keymaps/${entry_keymap}.keymap"

            # Copy the keymap named after the shield so ZMK's cmake finds it by exact match.
            cp "$keymap_path" "$NEW_CONFIG_PATH/${target}.keymap"
            build_firmware "$shield" "$target" "$entry_board" "$entry_keymap"
          done
        fi
      done

      echo "Cleaning up sandbox..."
      rm -rf "$SANDBOX_ROOT"
      echo ""
      done
    done
  done
done

# --- CALCULATE EXECUTION TIME ---
END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))
MINUTES=$(( ELAPSED / 60 ))
SECONDS=$(( ELAPSED % 60 ))
echo "=== BUILD COMPLETE ==="
echo "${MINUTES}m ${SECONDS}s @ $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
