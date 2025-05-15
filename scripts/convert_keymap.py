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

    # Define flags and parameters
    parser.add_argument('--list', action='store_true', help='List supported conversions and exit')

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

    # List options
    if args.list:
        print("Supported conversions:")
        for k in LAYOUT_MAPS.keys():
            print(f"  - {k}")
        sys.exit(0)

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
        before_keymap = match.group(1)
        old_keymap = match.group(2)
        after_keymap = match.group(3)
        
        print(f">> Found BASE keymap \n{old_keymap}")

        # Split the old keymap by lines
        lines = old_keymap.strip().split('\n')

        # Process each line
        new_lines = []
        print(">> Converting letter keys")
        for line in lines:
            # Split the line by spaces or other delimiters
            parts = line.split()
            new_parts = []

            for part in parts:
                if not part.startswith('&'):
                    # Extract key (removing ZMK behavior commands)
                    key = part.split()[1] if len(part.split()) > 1 else part
                    # Map the key to the conversion type if applicable
                    if key.upper() in initial_keymap:
                        print(key.upper(),end=":")
                        new_key = initial_keymap[key]
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
        print(f"\n>> Generated {out_file} \n{format_columns(new_keymap)}")
        return before_keymap + format_columns(new_keymap) + after_keymap
    
    def format_columns(text):    
        zmk_behavior = r'(&\w+)'

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

    converted_map = convert_keymap(keymap_contents)

    # Write the new keymap_contents to the output file
    with open(out_full_path, 'w') as file:
        file.write(converted_map)
    
    print("#####################################################################")
    print(f"Updated keymap written to {out_full_path}")
    print("#####################################################################")
if __name__ == "__main__":
    main()