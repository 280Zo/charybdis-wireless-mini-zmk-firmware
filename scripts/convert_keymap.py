import re
import os
import sys
import argparse
from layouts import LAYOUT_MAPS, OUTPUT_FILE_NAMES

def main():
    #####################################################################
    # Define variables & write output keymap file
    #####################################################################
    
    parser = argparse.ArgumentParser(
        description="Convert ZMK keymap files between layouts (e.g. QWERTY⇄Colemak DH)"
    )
    parser.add_argument(
        '-c', '--convert', 
        type=str, 
        choices=LAYOUT_MAPS.keys(),
        default='q2c',
        help="Conversion: 'q2c' QWERTY→ColemakDH, 'c2q' ColemakDH→QWERTY, etc."
    )
    parser.add_argument(
        '--in-path',
        type=str,
        required=True,
        help="Path to the input keymap file. Output is written alongside it."
    )
    args = parser.parse_args()

    conversion_type = args.convert
    full_path = args.in_path

    if conversion_type not in LAYOUT_MAPS:
        print(f"Error: Invalid conversion type '{conversion_type}'.")
        sys.exit(1)

    path, in_file = os.path.split(full_path)
    out_file = OUTPUT_FILE_NAMES.get(conversion_type, f"{conversion_type}.keymap")
    out_full_path = os.path.join(path, out_file)

    print("#####################################################################")
    print(f"Conversion: {conversion_type}")
    print(f"Input:      {in_file}")
    print(f"Output:     {out_file}")
    print("#####################################################################")

    # your mapping dict, e.g. {'Q':'Q', 'W':'W', 'E':'F', …}
    initial_keymap = LAYOUT_MAPS[conversion_type]

    # Read original keymap
    with open(full_path, 'r') as f:
        keymap_contents = f.read()

    #####################################################################
    # Conversion functions
    #####################################################################

    # 1) Precisely capture only the BASE bindings block
    base_pattern = re.compile(
        r'(^\s*BASE\s*\{\s*bindings\s*=\s*<\s*\n)'  # start of BASE layer
        r'(.*?)'                                    # everything inside
        r'(^\s*>\s*;)',                             # closing >;
        re.MULTILINE | re.DOTALL
    )

    # 2) Regex to match any all-caps token (your keycodes)
    code_pattern = re.compile(r'\b([A-Z][A-Z0-9_]*)\b')

    def replace_keymap(match):
        prefix, block, suffix = match.group(1), match.group(2), match.group(3)
        # single-pass substitution: only swap tokens present in initial_keymap
        def repl(tok_match):
            token = tok_match.group(1)
            return initial_keymap.get(token, token)
        new_block = code_pattern.sub(repl, block)
        return prefix + new_block + suffix

    # Perform conversion
    converted = base_pattern.sub(replace_keymap, keymap_contents)

    # Print out the new BASE layer for verification
    base_only = base_pattern.search(converted)
    if not base_only:
        print("⚠️  Warning: BASE layer not found in output!")
    # uncomment to print new baselayer to stdout
    # else:
        # print(">> Converted BASE layer:\n")
        # print(base_only.group(1) + base_only.group(2) + base_only.group(3))
        


    # Write to output file
    with open(out_full_path, 'w') as f:
        f.write(converted)

    print(f"→ Wrote updated keymap to {out_full_path}")

if __name__ == "__main__":
    main()
