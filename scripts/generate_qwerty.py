import re

# Define the file paths
# colemak_path = '/config/boards/shields/charybdis-mini-wireless/keymaps/charybdis_colemak_path_dh.keymap'
# qwerty_path  = '/config/boards/shields/charybdis-mini-wireless/keymaps/charybdis_qwerty.keymap'

colemak_path = 'in.keymap'
qwerty_path  = 'out.keymap'

# Define the Colemak DH to QWERTY mapping
colemak_to_qwerty = {
    # Top row (numbers and symbols are not included in this example)
    'Q': 'Q', 'W': 'W', 'F': 'E', 'P': 'R', 'B': 'T', 'J': 'Y', 'L': 'U', 'U': 'I', 'Y': 'O', 'APOS': 'P',

    # Home row
    'A': 'A', 'R': 'S', 'S': 'D', 'D': 'F', 'G': 'G', 'M': 'H', 'N': 'J', 'E': 'K', 'I': 'L', 'O': ';',

    # Bottom row
    'Z': 'Z', 'X': 'X', 'C': 'C', 'V': 'V', 'K': 'B', 'H': 'N',

    # Special keys (not row-specific)
    'TAB': 'TAB', 'DEL': 'DEL', 'BACKSPACE': 'BACKSPACE', 'ESCAPE': 'ESCAPE', 'RETURN': 'RETURN', 'SPACE': 'SPACE'
}


# Read the content of the input file
with open(colemak_path, 'r') as file:
    content = file.read()

# Find and replace the 'Base' keymap layout
def convert_colemak_to_qwerty(keymap_content):
    # Define regex pattern to find the 'Base' keymap section
    base_keymap_pattern = re.compile(r'(Base\s*\{\s*bindings\s*=\s*<\s*)(.*?)(\s*>;)', re.DOTALL)
    
    def replace_keymap(match):
        before_keymap = match.group(1)
        old_keymap = match.group(2)
        after_keymap = match.group(3)
        
        print(f"Found Base keymap \n{old_keymap}")

        # Split the old keymap by lines
        lines = old_keymap.strip().split('\n')

        # Process each line
        new_lines = []
        print("Processing keys")
        for line in lines:
            # Split the line by spaces or other delimiters
            parts = line.split()
            new_parts = []

            for part in parts:
                if not part.startswith('&'):
                    # Extract key (removing ZMK behavior commands)
                    key = part.split()[1] if len(part.split()) > 1 else part
                    # Map the key to QWERTY if applicable
                    if key.upper() in colemak_to_qwerty:
                        print(key.upper(),end=":")
                        new_key = colemak_to_qwerty[key]
                        print(new_key)
                        new_parts.append(part.replace(key, new_key))
                    else:
                        new_parts.append(part)
                else:
                    new_parts.append(part)
            
            # Join new parts for the line and add to new_lines
            new_lines.append(' '.join(new_parts))
            print(new_lines)

        # Join new lines to form the new keymap content
        new_keymap = '\n'.join(new_lines)
        print(f"Generated QWERTY map \n{new_keymap}")
        return before_keymap + new_keymap + after_keymap

    # Apply regex substitution to convert keymap
    new_content = base_keymap_pattern.sub(replace_keymap, keymap_content)
    
    return new_content

# Replace the 'Base' keymap with the QWERTY layout
qwerty_map = convert_colemak_to_qwerty(content)

# Write the new content to the output file
with open(qwerty_path, 'w') as file:
    file.write(qwerty_map)

print(f"Updated keymap written to {qwerty_path}")





# zmk_behaviors = [
#     # Key Press Behaviors
#     '&kp <key>',     # Key Press
#     '&kpr <key>',    # Key Press Repeat
#     '&kpt <key>',    # Key Press Toggle

#     # Modifier Behaviors
#     '&mt <modifier><key>',  # Modifier + Tap
#     '&hm <modifier><key>',  # Hold Modifier
#     '&mo <layer>',          # Momentary Layer

#     # Layer Behaviors
#     '&to <layer>',          # Layer Toggle
#     '&lt <layer>',          # Layer Tap

#     # Custom Actions
#     '&ca <action>',         # Custom Action

#     # Function Key Behaviors
#     '&fn <key>',            # Function Key

#     # Key Release Behaviors
#     '&kl <key>',            # Key Release

#     # Special Key Behaviors
#     '&caps_word',           # Caps Word
#     '&reset',               # Reset
#     '&debug',               # Debug

#     # Media and Control Keys
#     '&mute',                # Mute
#     '&vol_up',              # Volume Up
#     '&vol_down',            # Volume Down
#     '&play_pause'           # Play/Pause
    
#     # Custom
#     '&hr'                   # Home Row Modifier
# ]