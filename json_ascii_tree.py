#!/usr/bin/env python3

import argparse
import json
import re
import sys


# ============================================================
# Value formatting
# ============================================================

def value_text(value):
    """Represent a JSON value on one tree line."""

    if isinstance(value, dict):
        return "{}"

    if isinstance(value, list):
        return "[]"

    return json.dumps(
        value,
        ensure_ascii=False
    )


# ============================================================
# JSON -> tree
# ============================================================

def json_to_tree(data, pretty=False):
    """
    Convert a Python object into a tree.

    pretty=False:
        |-- "key": value
        `-- "key": value

    pretty=True:
        ├── "key": value
        └── "key": value
    """

    lines = [
        f"<root>: {value_text(data)}"
    ]

    def walk(value, prefix=""):

        if isinstance(value, dict):

            children = [
                (
                    json.dumps(
                        key,
                        ensure_ascii=False
                    ),
                    child
                )
                for key, child in value.items()
            ]

        elif isinstance(value, list):

            children = [
                (
                    f"[{i}]",
                    child
                )
                for i, child in enumerate(value)
            ]

        else:
            return


        for i, (label, child) in enumerate(children):

            is_last = (
                i == len(children) - 1
            )


            # ------------------------------------------------
            # Pretty Unicode tree
            # ------------------------------------------------

            if pretty:

                branch = (
                    "└── "
                    if is_last
                    else "├── "
                )

                child_prefix = prefix + (
                    "    "
                    if is_last
                    else "│   "
                )


            # ------------------------------------------------
            # Plain ASCII tree
            # ------------------------------------------------

            else:

                branch = (
                    "`-- "
                    if is_last
                    else "|-- "
                )

                child_prefix = prefix + (
                    "    "
                    if is_last
                    else "|   "
                )


            lines.append(
                prefix
                + branch
                + label
                + ": "
                + value_text(child)
            )


            if isinstance(child, (dict, list)) and child:

                walk(
                    child,
                    child_prefix
                )


    walk(data)

    return "\n".join(lines)


# ============================================================
# Tree -> JSON
# ============================================================

# Accept BOTH:
#
# ASCII:
# |-- "name": "Alice"
# `-- "age": 30
#
# Pretty:
# ├── "name": "Alice"
# └── "age": 30

ASCII_BRANCH_RE = re.compile(
    r"^(?P<prefix>(?:\|   |    )*)"
    r"(?:\|-- |`-- )"
    r"(?P<body>.*)$"
)

PRETTY_BRANCH_RE = re.compile(
    r"^(?P<prefix>(?:│   |    )*)"
    r"(?:├── |└── )"
    r"(?P<body>.*)$"
)

LIST_RE = re.compile(
    r"^\[(\d+)\]:\s*(.*)$"
)


def parse_json_value(text):
    """Parse a value using standard JSON syntax."""

    try:

        return json.loads(text)

    except json.JSONDecodeError as error:

        raise ValueError(
            f"Invalid JSON value: {text!r}"
        ) from error


def parse_dict_body(body):
    """
    Parse:

        "name": "Alice"
        "settings": {}
    """

    decoder = json.JSONDecoder()

    try:

        key, position = decoder.raw_decode(
            body
        )

    except json.JSONDecodeError as error:

        raise ValueError(
            f"Invalid dictionary key: {body!r}"
        ) from error


    if not isinstance(key, str):

        raise ValueError(
            "Dictionary keys must be quoted JSON strings."
        )


    remaining = body[position:].lstrip()


    if not remaining.startswith(":"):

        raise ValueError(
            f"Missing ':' after dictionary key: {body!r}"
        )


    value_string = remaining[1:].strip()

    value = parse_json_value(
        value_string
    )

    return key, value


def ascii_to_json(text):
    """
    Convert either ASCII or pretty Unicode tree format
    back into a Python object.
    """

    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip()
    ]


    if not lines:

        raise ValueError(
            "Tree input is empty."
        )


    # --------------------------------------------------------
    # Root
    # --------------------------------------------------------

    if not lines[0].startswith("<root>:"):

        raise ValueError(
            "First line must start with '<root>:'"
        )


    root_value = lines[0].split(
        ":",
        1
    )[1].strip()


    root = parse_json_value(
        root_value
    )


    # Maps depth -> container

    stack = {
        0: root
    }


    # --------------------------------------------------------
    # Remaining tree
    # --------------------------------------------------------

    for line_number, line in enumerate(
        lines[1:],
        start=2
    ):

        # Try ordinary ASCII first

        match = ASCII_BRANCH_RE.match(
            line
        )


        # Then try pretty Unicode tree

        if not match:

            match = PRETTY_BRANCH_RE.match(
                line
            )


        if not match:

            raise ValueError(
                f"Line {line_number}: "
                f"invalid tree structure:\n{line}"
            )


        prefix = match.group(
            "prefix"
        )

        body = match.group(
            "body"
        )


        # Every indentation unit is four characters.

        depth = (
            len(prefix) // 4
        ) + 1


        parent = stack.get(
            depth - 1
        )


        if not isinstance(
            parent,
            (dict, list)
        ):

            raise ValueError(
                f"Line {line_number}: "
                "parent is not a dictionary or list."
            )


        # ----------------------------------------------------
        # Dictionary
        # ----------------------------------------------------

        if isinstance(parent, dict):

            key, child = parse_dict_body(
                body
            )


            if key in parent:

                raise ValueError(
                    f"Line {line_number}: "
                    f"duplicate key {key!r}"
                )


            parent[key] = child


        # ----------------------------------------------------
        # List
        # ----------------------------------------------------

        else:

            list_match = LIST_RE.match(
                body
            )


            if not list_match:

                raise ValueError(
                    f"Line {line_number}: "
                    "expected '[0]: value'"
                )


            index = int(
                list_match.group(1)
            )


            child = parse_json_value(
                list_match.group(2).strip()
            )


            expected_index = len(
                parent
            )


            if index != expected_index:

                raise ValueError(
                    f"Line {line_number}: "
                    f"expected list index {expected_index}, "
                    f"got {index}"
                )


            parent.append(
                child
            )


        # Remove old deeper stack levels.

        for old_depth in list(stack):

            if old_depth >= depth:

                del stack[
                    old_depth
                ]


        # Nested object can become parent of following lines.

        if isinstance(
            child,
            (dict, list)
        ):

            stack[depth] = child


    return root


# ============================================================
# File helpers
# ============================================================

def read_text(filename):

    if filename == "-":

        return sys.stdin.read()


    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


def write_text(text, filename=None):

    if filename is None or filename == "-":

        print(text)

        return


    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(text)

        # Final newline
        file.write("\n")


# ============================================================
# Command-line interface
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert JSON to ASCII/pretty trees "
            "and tree structures back to JSON."
        )
    )


    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )


    # ========================================================
    # JSON -> ASCII/tree
    # ========================================================

    json_parser = subparsers.add_parser(
        "json2ascii",
        help="Convert JSON to tree"
    )


    json_parser.add_argument(
        "input",
        help="Input JSON file, or '-' for stdin"
    )


    json_parser.add_argument(
        "-o",
        "--output",
        help="Save reversible ASCII tree to this file"
    )


    json_parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help=(
            "Display a pretty Unicode tree in the terminal"
        )
    )


    # ========================================================
    # ASCII/tree -> JSON
    # ========================================================

    ascii_parser = subparsers.add_parser(
        "ascii2json",
        help="Convert ASCII/pretty tree to JSON"
    )


    ascii_parser.add_argument(
        "input",
        help="Input tree file, or '-' for stdin"
    )


    ascii_parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file"
    )


    ascii_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)"
    )


    ascii_parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help=(
            "Also display pretty formatted JSON "
            "in the terminal"
        )
    )


    args = parser.parse_args()


    # ========================================================
    # JSON -> tree
    # ========================================================

    if args.command == "json2ascii":

        json_text = read_text(
            args.input
        )


        data = json.loads(
            json_text
        )


        # ----------------------------------------------------
        # Plain reversible ASCII
        # ----------------------------------------------------

        ascii_tree = json_to_tree(
            data,
            pretty=False
        )


        # ----------------------------------------------------
        # Output file requested
        # ----------------------------------------------------

        if args.output:

            write_text(
                ascii_tree,
                args.output
            )


            # If --pretty, also display nice version
            # in terminal.

            if args.pretty:

                pretty_tree = json_to_tree(
                    data,
                    pretty=True
                )

                print(
                    pretty_tree
                )


            else:

                print(
                    f"Saved ASCII tree to: {args.output}"
                )


        # ----------------------------------------------------
        # No output file
        # ----------------------------------------------------

        else:

            tree = json_to_tree(
                data,
                pretty=args.pretty
            )

            print(
                tree
            )


    # ========================================================
    # Tree -> JSON
    # ========================================================

    elif args.command == "ascii2json":

        tree_text = read_text(
            args.input
        )


        data = ascii_to_json(
            tree_text
        )


        json_text = json.dumps(
            data,
            indent=args.indent,
            ensure_ascii=False
        )


        if args.output:

            write_text(
                json_text,
                args.output
            )


            if args.pretty:

                print(
                    json_text
                )

            else:

                print(
                    f"Saved JSON to: {args.output}"
                )


        else:

            print(
                json_text
            )


if __name__ == "__main__":
    main()
