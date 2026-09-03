#!/usr/bin/env python3

"""
Convert a human-friendly indented tree (such as tree.md) into JSON
suitable for d3js hierarchies.

Unlike json_ascii_tree.py's reversible ASCII tree format (quoted
"key": value lines with strict indentation), this format is meant to be
typed and edited by hand:

    Responsible research
    ├── Research ethics (3)
    │   ├── Ethical issues
    │   │   └── Humans and participants (6.6)
    │   └── Processes
    └── Research integrity (2)

Indentation blocks are always 4 characters wide, but the continuation
character before a deeper branch may be drawn as "│", "|", or left as
plain spaces once a parent's last child has already been drawn -- all
three are treated the same way. Branch markers may be the Unicode
"├── " / "└── " or the ASCII "|-- " / "`-- " forms.

Trailing parenthetical annotations on a label -- "(3)", "(link)",
"(missing)", "([link](https://...))" and so on -- are kept as-is, as
part of the node's display name. They are not split out into separate
metadata fields.
"""

import argparse
import json
import re
import sys


# ============================================================
# Line parsing
# ============================================================

BRANCH_RE = re.compile(
    r"^(?P<prefix>.*?)"
    r"(?:├──|└──|\|--|`--)"
    r" ?"
    r"(?P<label>.*)$"
)


def is_blank_separator(line):
    """A line that carries no label, only bar/space filler."""

    return line.strip(" |│\t") == ""


def parse_line(line, line_number):
    """
    Return (depth, label) for a branch line, or None for a blank
    separator line. Raises ValueError for anything else.
    """

    match = BRANCH_RE.match(line)

    if not match:

        if is_blank_separator(line):
            return None

        raise ValueError(
            f"Line {line_number}: could not find a branch marker "
            f"(expected '├── ', '└── ', '|-- ' or '`-- '):\n{line}"
        )

    prefix = match.group("prefix")

    if len(prefix) % 4 != 0:
        raise ValueError(
            f"Line {line_number}: indentation is not a multiple of "
            f"4 characters:\n{line}"
        )

    depth = len(prefix) // 4 + 1
    label = match.group("label").rstrip()

    return depth, label


# ============================================================
# Tree -> JSON
# ============================================================

def tree_md_to_json(text):

    lines = text.splitlines()

    non_blank = [
        (number, line)
        for number, line in enumerate(lines, start=1)
        if line.strip() != ""
    ]

    if not non_blank:
        raise ValueError("Tree input is empty.")

    root_number, root_line = non_blank[0]
    root_name = root_line.strip()

    root = {"name": root_name}

    stack = {0: root}

    for line_number, line in non_blank[1:]:

        parsed = parse_line(line, line_number)

        if parsed is None:
            continue

        depth, name = parsed

        parent = stack.get(depth - 1)

        if parent is None:
            raise ValueError(
                f"Line {line_number}: indentation jumps to depth "
                f"{depth} without a parent at depth {depth - 1}:\n{line}"
            )

        node = {"name": name}

        parent.setdefault("children", []).append(node)

        for old_depth in list(stack):
            if old_depth >= depth:
                del stack[old_depth]

        stack[depth] = node

    return root


# ============================================================
# File helpers
# ============================================================

def read_text(filename):

    if filename == "-":
        return sys.stdin.read()

    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def write_text(text, filename=None):

    if filename is None or filename == "-":
        print(text)
        return

    with open(filename, "w", encoding="utf-8") as file:
        file.write(text)

        if not text.endswith("\n"):
            file.write("\n")


# ============================================================
# Command-line interface
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert a human-friendly indented tree (e.g. tree.md) "
            "into JSON for d3js."
        )
    )

    parser.add_argument(
        "input",
        help="Input tree file, or '-' for stdin",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file",
    )

    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)",
    )

    parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help=(
            "Also print the formatted JSON in the terminal "
            "when -o is used"
        ),
    )

    args = parser.parse_args()

    tree_text = read_text(args.input)
    data = tree_md_to_json(tree_text)

    json_text = json.dumps(
        data,
        indent=args.indent,
        ensure_ascii=False,
    )

    if args.output:

        write_text(json_text, args.output)

        if args.pretty:
            print(json_text)
        else:
            print(f"Saved JSON to: {args.output}")

    else:
        print(json_text)


if __name__ == "__main__":
    main()
