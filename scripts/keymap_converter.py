#!/usr/bin/env python3
import re
import os
import sys
import argparse
from layouts import LAYOUT_MAPS


BASE_PATTERN = re.compile(
    r'(^\s*BASE\s*\{[\s\S]*?bindings\s*=\s*<\s*(?:\r?\n))'  # BASE header
    r'([\s\S]*?)'                                                  # block contents
    r'(^\s*>\s*;)',                                                # footer
    re.MULTILINE
)
CODE_PATTERN = re.compile(r'\b([A-Z][A-Z0-9_]*)\b')


def print_available_maps():
    """Pretty-print available source -> destination maps in columnar format."""
    print("Available maps:")
    grouped = {}
    for (src, dst) in LAYOUT_MAPS.keys():
        grouped.setdefault(src, []).append(dst)

    max_src_len = max(len(src) for src in grouped)
    for src, dsts in grouped.items():
        dsts_str = ", ".join(sorted(dsts))
        print(f"  {src.ljust(max_src_len)} -> {dsts_str}")


def convert_keymap_contents(keymap_contents, mapping):
    """Return keymap contents with tokens replaced according to mapping."""

    def replace_keymap(match):
        prefix, block, suffix = match.group(1), match.group(2), match.group(3)

        def repl(tok_match):
            token = tok_match.group(1)
            return mapping.get(token, token)

        new_block = CODE_PATTERN.sub(repl, block)
        return prefix + new_block + suffix

    return BASE_PATTERN.sub(replace_keymap, keymap_contents)


def main():
    parser = argparse.ArgumentParser(
        description="Convert ZMK keymap files between layouts (e.g. QWERTY->Colemak DH)"
    )
    map_group = parser.add_mutually_exclusive_group()
    map_group.add_argument(
        '-m', '--map',
        type=str,
        help=(
            "Conversion map to apply (e.g. qwerty->colemakdh, qwerty:colemakdh, "
            "colemakdh->qwerty)."
        )
    )
    map_group.add_argument(
        '--all',
        action='store_true',
        help="Convert using every available qwerty->* map"
    )
    parser.add_argument(
        '-i', '--in',
        dest="in_path",
        type=str,
        help="Path to the input .keymap file"
    )
    parser.add_argument(
        '-o', '--out',
        dest="out_path",
        type=str,
        help="Path to write the converted .keymap file (default: alongside input)"
    )
    parser.add_argument(
        '--list-maps',
        action="store_true",
        help="List available maps and exit"
    )
    args = parser.parse_args()

    # Handle --list-maps
    if args.list_maps:
        print_available_maps()
        sys.exit(0)

    # Require input path if not listing maps
    if not args.in_path:
        parser.error("the following arguments are required: -i/--in")

    # Require either --map or --all
    if not (args.map or args.all):
        parser.error("one of the arguments -m/--map --all is required")

    # Prepare map list
    mappings_to_run = []

    if args.map:
        separator = None
        for candidate in ("->", ":"):
            if candidate in args.map:
                separator = candidate
                break

        if separator is None:
            print(
                f"Invalid map format '{args.map}'. Expected 'src->dst' or 'src:dst'.\n"
            )
            print_available_maps()
            sys.exit(1)

        src, dst = args.map.split(separator, 1)
        map_key = (src.strip().lower(), dst.strip().lower())

        if map_key not in LAYOUT_MAPS:
            print(f"[ERROR] Map '{args.map}' not found.\n")
            print_available_maps()
            sys.exit(1)

        mappings_to_run.append((map_key, LAYOUT_MAPS[map_key]))
    else:
        for map_key, mapping in LAYOUT_MAPS.items():
            src, dst = map_key
            if src == "qwerty":
                mappings_to_run.append((map_key, mapping))

        if not mappings_to_run:
            print("[ERROR] No qwerty->* maps available.")
            sys.exit(1)

        mappings_to_run.sort(key=lambda item: item[0][1])

        if args.out_path:
            print("[WARN] --out is ignored when using --all")

    # Paths
    in_file = args.in_path
    if not os.path.isfile(in_file):
        print(f"[ERROR] Input file not found: {in_file}")
        sys.exit(1)

    with open(in_file, 'r') as f:
        keymap_contents = f.read()

    input_dir = os.path.dirname(in_file) or "."

    for map_key, mapping in mappings_to_run:
        src, dst = map_key
        if args.all:
            out_file = os.path.join(input_dir, f"{dst}.keymap")
        else:
            out_file = args.out_path or os.path.join(input_dir, f"{dst}.keymap")

        converted = convert_keymap_contents(keymap_contents, mapping)

        with open(out_file, 'w') as f:
            f.write(converted)

        print(f"[OK] Converted {in_file} -> {out_file}")


if __name__ == "__main__":
    main()
