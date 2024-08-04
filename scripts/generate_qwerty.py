import re
import os

# Define the file paths
colemak_file = 'charybdis_colemak_dh.keymap'
qwerty_file  = 'charybdis_qwerty.keymap'

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

def format_columns(text):    
    zmk_behavior = r'(&\w{2})'

    # Split the input text into lines
    lines = text.strip().split('\n')
    
    # Split each line into columns
    split_lines = [re.split(zmk_behavior,line) for line in lines]
    
    # Determine the number of columns
    num_columns = max(len(line) for line in split_lines)
    
    # Calculate the maximum width for each column
    column_widths = [0] * num_columns
    for line in split_lines:
        for i, item in enumerate(line):
            column_widths[i] = max(column_widths[i], len(item))
    
    # Format each line with the calculated column widths
    formatted_lines = []
    for line in split_lines:
        formatted_line = ''.join(f"{item:<{column_widths[i] + 1}}" for i, item in enumerate(line))
        formatted_lines.append(formatted_line)
    
    # Join all formatted lines
    formatted_text = '\n'.join(formatted_lines)
    return formatted_text


# Read the content of the input file
gh_workspace  = os.getenv('GITHUB_WORKSPACE')
relative_path = 'config/boards/shields/charybdis-mini-wireless/keymaps'
absolute_path = os.path.join(gh_workspace, relative_path)
os.chdir(absolute_path)
with open(colemak_file, 'r') as file:
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

        # Join new lines to form the new keymap content
        new_keymap = '\n'.join(new_lines)
        print("")
        print(f"Generated QWERTY map \n{format_columns(new_keymap)}")
        return before_keymap + format_columns(new_keymap) + after_keymap

    # Apply regex substitution to convert keymap
    new_content = base_keymap_pattern.sub(replace_keymap, keymap_content)
    
    return new_content

# Replace the 'Base' keymap with the QWERTY layout
qwerty_map = convert_colemak_to_qwerty(content)

# Write the new content to the output file
with open(qwerty_file, 'w') as file:
    file.write(qwerty_map)

print(f"\nUpdated keymap written to {os.getcwd()+'/'+qwerty_file}")