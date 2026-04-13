#!/usr/bin/env python3
"""
Quick usage for this repo:

1) List available maps:
   python3 scripts/keymap_converter.py --list-maps

2) Fan out from one source keymap to all other supported keymaps (excluding
   the source layout):
   python3 scripts/keymap_converter.py \
     -i config/keymaps/colemak_dh.keymap \
     --all

3) Single conversion:
   python3 scripts/keymap_converter.py \
     -i config/keymaps/qwerty.keymap \
     -m qwerty->graphite

Notes:
- This script rewrites only the BASE layer `bindings = < ... >` block.
- All non-BASE layers/includes/comments are copied from the source file.
- `--all` infers the source layout from the input filename stem (for example,
  `colemak_dh.keymap` -> `colemak_dh`). Use `--source-layout` to override.
"""

import re
import os
import sys
import argparse
from collections import deque
from pathlib import Path
from layouts import LAYOUT_MAPS


BASE_PATTERN = re.compile(
    r'(^\s*BASE\s*\{[\s\S]*?bindings\s*=\s*<\s*(?:\r?\n))'  # BASE header
    r'([\s\S]*?)'                                            # block contents
    r'(^\s*>\s*;)',                                          # footer
    re.MULTILINE
)
CODE_PATTERN = re.compile(r'\b([A-Z][A-Z0-9_]*)\b')


def normalize_layout_name(name):
    """Normalize layout names for alias matching."""
    return re.sub(r'[^a-z0-9]+', '', name.lower())


def build_layout_metadata():
    """
    Build canonical layout names and alias resolution table.

    Canonical output layout names come from qwerty->* maps plus qwerty itself.
    """
    target_layouts = {"qwerty"}
    all_layouts = set()
    for src, dst in LAYOUT_MAPS.keys():
        all_layouts.add(src)
        all_layouts.add(dst)
        if src == "qwerty":
            target_layouts.add(dst)

    alias_to_canonical = {}
    for name in sorted(target_layouts):
        alias_to_canonical[normalize_layout_name(name)] = name
    for name in sorted(all_layouts):
        alias_to_canonical.setdefault(normalize_layout_name(name), name)

    return target_layouts, alias_to_canonical


def resolve_layout_name(name, alias_to_canonical):
    """Resolve a user/file layout name to a canonical layout id."""
    return alias_to_canonical.get(normalize_layout_name(name))


def build_canonical_maps(alias_to_canonical):
    """Convert LAYOUT_MAPS keys to canonical names."""
    canonical_maps = {}
    for (src, dst), mapping in LAYOUT_MAPS.items():
        canonical_src = resolve_layout_name(src, alias_to_canonical)
        canonical_dst = resolve_layout_name(dst, alias_to_canonical)
        if canonical_src and canonical_dst:
            canonical_maps[(canonical_src, canonical_dst)] = mapping
    return canonical_maps


def find_conversion_path(src, dst, canonical_maps):
    """
    Find a conversion path from src to dst using available maps.

    Returns a list of (step_src, step_dst, mapping).
    """
    if src == dst:
        return []

    graph = {}
    for step_src, step_dst in canonical_maps.keys():
        graph.setdefault(step_src, []).append(step_dst)

    queue = deque([src])
    previous = {src: None}

    while queue:
        node = queue.popleft()
        for nxt in graph.get(node, []):
            if nxt in previous:
                continue
            previous[nxt] = node
            if nxt == dst:
                queue.clear()
                break
            queue.append(nxt)

    if dst not in previous:
        return None

    nodes = [dst]
    while nodes[-1] != src:
        nodes.append(previous[nodes[-1]])
    nodes.reverse()

    path = []
    for i in range(len(nodes) - 1):
        step_src = nodes[i]
        step_dst = nodes[i + 1]
        path.append((step_src, step_dst, canonical_maps[(step_src, step_dst)]))
    return path


def apply_conversion_path(keymap_contents, path):
    """Apply each mapping in a conversion path."""
    converted = keymap_contents
    for _, _, mapping in path:
        converted = convert_keymap_contents(converted, mapping)
    return converted


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
    """Return keymap contents with tokens replaced in BASE layer bindings."""

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
        help="Convert to every supported layout except the source layout"
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
    parser.add_argument(
        '--source-layout',
        type=str,
        help="Override source layout for --all (default: infer from input filename stem)"
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

    in_file = args.in_path
    if not os.path.isfile(in_file):
        print(f"[ERROR] Input file not found: {in_file}")
        sys.exit(1)

    target_layouts, alias_to_canonical = build_layout_metadata()
    canonical_maps = build_canonical_maps(alias_to_canonical)
    conversions_to_run = []

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

        raw_src, raw_dst = args.map.split(separator, 1)
        src = resolve_layout_name(raw_src.strip(), alias_to_canonical)
        dst = resolve_layout_name(raw_dst.strip(), alias_to_canonical)

        if not src or not dst:
            print(f"[ERROR] Map '{args.map}' contains unknown layout(s).\n")
            print_available_maps()
            sys.exit(1)

        path = find_conversion_path(src, dst, canonical_maps)
        if path is None:
            print(f"[ERROR] No conversion path found for '{raw_src.strip()}->{raw_dst.strip()}'.\n")
            print_available_maps()
            sys.exit(1)

        conversions_to_run.append((src, dst, path))
    else:
        source_hint = args.source_layout or Path(in_file).stem
        source_layout = resolve_layout_name(source_hint, alias_to_canonical)

        if not source_layout:
            print(
                f"[ERROR] Could not infer source layout from '{source_hint}'. "
                "Use --source-layout."
            )
            print_available_maps()
            sys.exit(1)

        for dst in sorted(target_layouts):
            if dst == source_layout:
                continue
            path = find_conversion_path(source_layout, dst, canonical_maps)
            if path is None:
                print(f"[ERROR] No conversion path found for '{source_layout}->{dst}'.")
                sys.exit(1)
            conversions_to_run.append((source_layout, dst, path))

        if not conversions_to_run:
            print("[ERROR] No destination layouts found for --all.")
            sys.exit(1)

        if args.out_path:
            print("[WARN] --out is ignored when using --all")

    with open(in_file, 'r') as f:
        keymap_contents = f.read()

    input_dir = os.path.dirname(in_file) or "."
    input_abs = os.path.abspath(in_file)

    for src, dst, path in conversions_to_run:
        if args.all:
            out_file = os.path.join(input_dir, f"{dst}.keymap")
            if os.path.abspath(out_file) == input_abs:
                continue
        else:
            out_file = args.out_path or os.path.join(input_dir, f"{dst}.keymap")

        converted = apply_conversion_path(keymap_contents, path)

        with open(out_file, 'w') as f:
            f.write(converted)

        route = " -> ".join([src] + [step_dst for _, step_dst, _ in path]) if path else src
        print(f"[OK] Converted {in_file} -> {out_file} ({route})")


if __name__ == "__main__":
    main()
