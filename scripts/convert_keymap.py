import re
import os
import sys
import argparse

def main():
    #####################################################################
    # Define variables & write output keymap file
    #####################################################################
    
    # Create the parser
    parser = argparse.ArgumentParser(description="A script that converts keymap files from qwerty > Colemak DH or colemak DH to QWERTY")
        
    # Define flags and parameters
    parser.add_argument(
        '-c', '--convert', 
        type=str, 
        choices=['q2c', 'c2q'], 
        default='q2c',
        help="Specify the conversion: 'q2c' will convert QWERTY to Colemak DH, 'c2q' will convert Colemak DH to QWERTY (default: 'q2c')"
    )
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Set the variable for the chosen option
    conversion_type = args.convert

    # Check argument values and convert keymap
    output_file = ""
    if conversion_type == 'q2c':
        input_file  = 'charybdis_qwerty.keymap'
        output_file = 'charybdis_colemak_dh.keymap'
    elif conversion_type == 'c2q':
        input_file  = 'charybdis_colemak_dh.keymap'
        output_file = 'charybdis_qwerty.keymap'
    else:
        print("Error: Invalid conversion type selected.")
        sys.exit(1)
        
    print(f"Selected conversion type: {conversion_type}")
    converted_map = convert_keymap(keymap_contents)

    # Write the new keymap_contents to the output file
    os.chdir(os.getenv('GITHUB_WORKSPACE'))
    with open(output_file, 'w') as file:
        file.write(converted_map)
    
    print(f"\nUpdated keymap written to {os.getcwd()+'/'+qwerty_file}")
    
    #####################################################################
    # Define conversions
    #####################################################################

    # Define the QWERTY to Colemak DH mapping
    qwerty_to_colemak = {
        # Top row (numbers and symbols are not included in this example)
        'Q': 'Q', 'W': 'W', 'E': 'F', 'R': 'P', 'T': 'B', 'Y': 'J', 'U': 'L', 'I': 'U', 'O': 'Y', 'P': 'APOS',
        # Home row
        'A': 'A', 'S': 'R', 'D': 'S', 'F': 'D', 'G': 'G', 'H': 'M', 'J': 'N', 'K': 'E', 'L': 'I', 'SEMICOLON': 'O',
        # Bottom row
        'Z': 'Z', 'X': 'X', 'C': 'C', 'V': 'V', 'B': 'K', 'N': 'H',
        # Special keys (not row-specific)
        'TAB': 'TAB', 'DEL': 'DEL', 'BACKSPACE': 'BACKSPACE', 'ESCAPE': 'ESCAPE', 'RETURN': 'RETURN', 'SPACE': 'SPACE'
    }
    
    # Define the Colemak DH to QWERTY mapping
    colemak_to_qwerty = {
        # Top row (numbers and symbols are not included in this example)
        'Q': 'Q', 'W': 'W', 'F': 'E', 'P': 'R', 'B': 'T', 'J': 'Y', 'L': 'U', 'U': 'I', 'Y': 'O', 'APOS': 'P',
        # Home row
        'A': 'A', 'R': 'S', 'S': 'D', 'D': 'F', 'G': 'G', 'M': 'H', 'N': 'J', 'E': 'K', 'I': 'L', 'O': 'SEMICOLON',
        # Bottom row
        'Z': 'Z', 'X': 'X', 'C': 'C', 'V': 'V', 'K': 'B', 'H': 'N',
        # Special keys (not row-specific)
        'TAB': 'TAB', 'DEL': 'DEL', 'BACKSPACE': 'BACKSPACE', 'ESCAPE': 'ESCAPE', 'RETURN': 'RETURN', 'SPACE': 'SPACE'
    }
    
    #####################################################################
    # Read and store input keymap 
    #####################################################################

    # Read the content of the keymap_contents
    gh_workspace  = os.getenv('GITHUB_WORKSPACE')
    relative_path = 'config/boards/shields/charybdis-mini-wireless/keymaps'
    absolute_path = os.path.join(gh_workspace, relative_path)
    os.chdir(absolute_path)
    with open(input_file, 'r') as keymap_file:
        keymap_contents = keymap_file.read()

    # Define regex pattern to find the 'Base' keymap section
    base_keymap_pattern = re.compile(r'(Base\s*\{\s*bindings\s*=\s*<\s*)(.*?)(\s*>;)', re.DOTALL)
    
    #####################################################################
    # Functions
    #####################################################################

    # Convert keymap
    def convert_keymap(keymap_contents):        
        # Apply regex substitution to convert keymap
        new_keymap_contents = base_keymap_pattern.sub(replace_keymap, keymap_contents)
        return new_keymap_contents
    
    # Find and replace the 'Base' keymap layer
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
                    if key.upper() in qwerty_to_colemak:
                        print(key.upper(),end=":")
                        new_key = qwerty_to_colemak[key]
                        print(new_key)
                        new_parts.append(part.replace(key, new_key))
                    else:
                        new_parts.append(part)
                else:
                    new_parts.append(part)
            
            # Join new parts for the line and add to new_lines
            new_lines.append(' '.join(new_parts))

        # Join new lines to form the new keymap keymap_contents
        new_keymap = '\n'.join(new_lines)
        print("")
        print(f"Generated QWERTY map \n{format_columns(new_keymap)}")
        return before_keymap + format_columns(new_keymap) + after_keymap
    
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

if __name__ == "__main__":
    main()