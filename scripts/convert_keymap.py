import re
import os
import sys
import argparse
from layouts import LAYOUT_MAPS, OUTPUT_FILE_NAMES

def main():
    #####################################################################
    # Define variables & write output keymap file
    #####################################################################
    
    # Create the parser
    parser = argparse.ArgumentParser(description="A script that converts ZMK keymap files from QWERTY <|> Colemak DH")

    parser.add_argument(
        '-c', '--convert', 
        type=str, 
        choices=LAYOUT_MAPS.keys(),
        default='q2c',
        help="Specify the conversion: 'q2c' will convert QWERTY to Colemak DH, 'c2q' will convert Colemak DH to QWERTY (default: 'q2c')"
    )

    parser.add_argument(
        '--in-path',
        type=str,
        required=True,
        help="Path to the input keymap file. This is the path where the ouitput will be stored as well"
    )

    # Parse the arguments
    args = parser.parse_args()

    # Set the variable for the chosen option
    conversion_type = args.convert
    full_path = args.in_path
    
    # Check argument values and convert keymap
    if conversion_type not in LAYOUT_MAPS:
        print(f"Error: Invalid conversion type '{conversion_type}'.")
        sys.exit(1)

    path, in_file = os.path.split(full_path)
    out_file = OUTPUT_FILE_NAMES.get(conversion_type, f"{conversion_type}.keymap")
    out_full_path = os.path.join(path, out_file)

    print("#####################################################################")
    print(f"Selected conversion type: {conversion_type}")
    print(f"path:........{path}")
    print(f"input_file:..{in_file}")
    print(f"out_file:....{out_file}")
    print("#####################################################################")

    #####################################################################
    # Define conversions
    #####################################################################   
    try:
        initial_keymap = LAYOUT_MAPS[conversion_type]
    except KeyError:
        print(f"Unsupported conversion: {conversion_type}")
        sys.exit(1)
    
    #####################################################################
    # Read and store input keymap 
    #####################################################################

    # Read the content of the keymap_contents
    with open(full_path, 'r') as keymap_file:
        keymap_contents = keymap_file.read()
    
    #####################################################################
    # Functions
    #####################################################################

    def convert_keymap(keymap_contents):   
        # Define regex pattern to find the 'Base' keymap section
        base_keymap_pattern = re.compile(r'(BASE\s*\{\s*bindings\s*=\s*<\s*)(.*?)(\s*>;)', re.DOTALL)     
        
        # Apply regex substitution to convert keymap
        new_keymap_contents = base_keymap_pattern.sub(replace_keymap, keymap_contents)
        return new_keymap_contents
    
    # Find and replace the 'BASE' keymap layer
    def replace_keymap(match):
        before, block, after = match.group(1), match.group(2), match.group(3)
        new_block = block

        # For each mapping, do an in-place word-boundary replace.
        # This touches only the key names (e.g. 'Q', 'X', 'SEMICOLON') 
        # and leaves every space, comment, and box-drawing character untouched.
        for old, new in initial_keymap.items():
            # \b ensures we only match whole words like 'A' or 'SEMICOLON'
            pattern = rf"\b{re.escape(old)}\b"
            new_block = re.sub(pattern, new, new_block)

        return before + new_block + after
    
    converted_map = convert_keymap(keymap_contents)

    # ——— New: print the converted BASE layer for verification ———
    print(">> Converted BASE layer:\n")
    print(converted_map)  
    print("—————————————————————————")

    # Write the new keymap_contents to the output file
    with open(out_full_path, 'w') as file:
        file.write(converted_map)
    
    print("#####################################################################")
    print(f"Updated keymap written to {out_full_path}")
    print("#####################################################################")
if __name__ == "__main__":
    main()