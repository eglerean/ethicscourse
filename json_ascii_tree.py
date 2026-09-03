#!/usr/bin/env python3

import argparse
import json
import re
import sys


# ============================================================
# JSON value formatting
# ============================================================

def value_text(value):
    """Represent a JSON value on one tree line."""

    if isinstance(value, dict):
        return "{}"

    if isinstance(value, list):
        return "[]"

    return json.dumps(value, ensure_ascii=False)


# ============================================================
# JSON -> reversible tree
# ============================================================

def json_to_tree(data, pretty=False):
    """
    Convert JSON data to a reversible tree.

    pretty=False:
        |-- "key": value
        `-- "key": value

    pretty=True:
        ├── "key": value
        └── "key": value
    """

    lines = [f"<root>: {value_text(data)}"]

    def walk(value, prefix=""):

        if isinstance(value, dict):
            children = [
                (
                    json.dumps(key, ensure_ascii=False),
                    child,
                )
                for key, child in value.items()
            ]

        elif isinstance(value, list):
            children = [
                (f"[{i}]", child)
                for i, child in enumerate(value)
            ]

        else:
            return

        for i, (label, child) in enumerate(children):

            is_last = i == len(children) - 1

            if pretty:
                branch = "└── " if is_last else "├── "
                child_prefix = prefix + (
                    "    " if is_last else "│   "
                )
            else:
                branch = "`-- " if is_last else "|-- "
                child_prefix = prefix + (
                    "    " if is_last else "|   "
                )

            lines.append(
                prefix
                + branch
                + label
                + ": "
                + value_text(child)
            )

            if isinstance(child, (dict, list)) and child:
                walk(child, child_prefix)

    walk(data)

    return "\n".join(lines)


# ============================================================
# JSON -> compact display-only tree
# ============================================================

DEFAULT_LABEL_KEYS = ("name", "label", "title", "id")
DEFAULT_SKIP_KEYS = ("children", "items")


def json_to_compact_tree(
    data,
    label_keys=DEFAULT_LABEL_KEYS,
    skip_keys=DEFAULT_SKIP_KEYS,
):
    """
    Produce a simplified display-only Unicode tree.

    The compact format intentionally hides:
      - JSON values used only as metadata
      - list indices
      - wrapper keys such as "children" and "items"

    Example:
        parent
        ├── child1
        └── child2

    This representation is NOT reversible.
    """

    lines = []

    def scalar_text(value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        return str(value)

    def object_label(value):
        """Return a useful label for a dict or scalar when possible."""

        if isinstance(value, dict):
            for key in label_keys:
                if key in value and not isinstance(
                    value[key], (dict, list)
                ):
                    return scalar_text(value[key])

        elif not isinstance(value, (dict, list)):
            return scalar_text(value)

        return None

    def children_of(value):
        """
        Return (label, child_value) pairs for meaningful child nodes.
        """

        children = []

        if isinstance(value, dict):

            for key, child in value.items():

                # Fields used as the current object's label are metadata.
                if key in label_keys:
                    continue

                # Hide common wrapper keys such as "children" and "items".
                if key in skip_keys:

                    if isinstance(child, list):
                        for element in child:
                            label = object_label(element)

                            if label is None:
                                label = "node"

                            children.append((label, element))

                    elif isinstance(child, dict):
                        for child_key, child_value in child.items():

                            label = object_label(child_value)

                            # For dictionaries like:
                            # "children": {"child1": {...}}
                            # prefer the dictionary key.
                            if label is None:
                                label = str(child_key)

                            children.append(
                                (label, child_value)
                            )

                    elif child is not None:
                        children.append(
                            (scalar_text(child), child)
                        )

                    continue

                # Normal dictionary fields become nodes.
                if isinstance(child, (dict, list)):
                    label = object_label(child) or str(key)
                    children.append((label, child))
                else:
                    # Compact mode is primarily about structure.
                    # Show scalar leaves by their key when possible.
                    children.append((str(key), child))

        elif isinstance(value, list):

            for element in value:
                label = object_label(element)

                if label is None:
                    label = "node"

                children.append((label, element))

        return children

    def walk(
        value,
        label,
        prefix="",
        is_last=True,
        is_root=False,
    ):

        if is_root:
            lines.append(str(label))
        else:
            branch = "└── " if is_last else "├── "
            lines.append(prefix + branch + str(label))

        if is_root:
            child_prefix = ""
        else:
            child_prefix = prefix + (
                "    " if is_last else "│   "
            )

        children = children_of(value)

        for i, (child_label, child_value) in enumerate(children):
            walk(
                child_value,
                child_label,
                prefix=child_prefix,
                is_last=(i == len(children) - 1),
                is_root=False,
            )

    # Try to pick a meaningful root label.
    if isinstance(data, dict) and len(data) == 1:
        root_label = next(iter(data))
        root_value = data[root_label]

    else:
        root_label = object_label(data) or "root"
        root_value = data

    walk(
        root_value,
        root_label,
        is_root=True,
    )

    return "\n".join(lines)


# ============================================================
# Reversible tree -> JSON
# ============================================================

# Accept both plain ASCII:
# |-- "name": "Alice"
# `-- "age": 30
#
# and pretty Unicode:
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
    """Parse one tree value using normal JSON syntax."""

    try:
        return json.loads(text)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON value: {text!r}"
        ) from error


def parse_dict_body(body):
    """
    Parse a dictionary entry such as:

        "name": "Alice"
        "settings": {}
    """

    decoder = json.JSONDecoder()

    try:
        key, position = decoder.raw_decode(body)

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

    if value_string == "":
        raise ValueError(
            f"Missing value after dictionary key: {body!r}"
        )

    value = parse_json_value(value_string)

    return key, value


def tree_to_json(text):
    """
    Convert a reversible ASCII or Unicode tree back into JSON.

    Compact tree output cannot be parsed because compact mode
    intentionally discards information.
    """

    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError("Tree input is empty.")

    if not lines[0].startswith("<root>:"):
        raise ValueError(
            "First line must start with '<root>:'. "
            "Compact tree output is display-only and cannot "
            "be converted back to JSON."
        )

    root_value = lines[0].split(":", 1)[1].strip()
    root = parse_json_value(root_value)

    stack = {0: root}

    for line_number, line in enumerate(
        lines[1:],
        start=2,
    ):

        match = ASCII_BRANCH_RE.match(line)

        if not match:
            match = PRETTY_BRANCH_RE.match(line)

        if not match:
            raise ValueError(
                f"Line {line_number}: invalid tree structure:\n"
                f"{line}"
            )

        prefix = match.group("prefix")
        body = match.group("body")

        # Each indentation block is four characters.
        depth = (len(prefix) // 4) + 1

        parent = stack.get(depth - 1)

        if not isinstance(parent, (dict, list)):
            raise ValueError(
                f"Line {line_number}: parent is not "
                "a dictionary or list."
            )

        if isinstance(parent, dict):

            key, child = parse_dict_body(body)

            if key in parent:
                raise ValueError(
                    f"Line {line_number}: duplicate key {key!r}"
                )

            parent[key] = child

        else:

            list_match = LIST_RE.match(body)

            if not list_match:
                raise ValueError(
                    f"Line {line_number}: expected list item "
                    "such as '[0]: value'."
                )

            index = int(list_match.group(1))
            child = parse_json_value(
                list_match.group(2).strip()
            )

            expected_index = len(parent)

            if index != expected_index:
                raise ValueError(
                    f"Line {line_number}: expected list index "
                    f"{expected_index}, got {index}."
                )

            parent.append(child)

        # Drop no-longer-active deeper levels.
        for old_depth in list(stack):
            if old_depth >= depth:
                del stack[old_depth]

        if isinstance(child, (dict, list)):
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
        encoding="utf-8",
    ) as file:
        return file.read()


def write_text(text, filename=None):

    if filename is None or filename == "-":
        print(text)
        return

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(text)

        if not text.endswith("\n"):
            file.write("\n")


# ============================================================
# Command-line interface
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Convert JSON to reversible ASCII/Unicode trees, "
            "display compact trees, and convert reversible "
            "trees back to JSON."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------------
    # JSON -> tree
    # --------------------------------------------------------

    json_parser = subparsers.add_parser(
        "json2ascii",
        help="Convert JSON to tree output",
    )

    json_parser.add_argument(
        "input",
        help="Input JSON file, or '-' for stdin",
    )

    json_parser.add_argument(
        "-o",
        "--output",
        help=(
            "Save the reversible plain ASCII tree to this file"
        ),
    )

    display_group = json_parser.add_mutually_exclusive_group()

    display_group.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help=(
            "Display the reversible tree using Unicode "
            "tree characters"
        ),
    )

    display_group.add_argument(
        "-c",
        "--compact",
        action="store_true",
        help=(
            "Display a simplified node-only Unicode tree. "
            "This format is not reversible."
        ),
    )

    json_parser.add_argument(
        "--label-keys",
        nargs="+",
        default=list(DEFAULT_LABEL_KEYS),
        metavar="KEY",
        help=(
            "Keys used as node labels in compact mode "
            "(default: name label title id)"
        ),
    )

    json_parser.add_argument(
        "--skip-keys",
        nargs="+",
        default=list(DEFAULT_SKIP_KEYS),
        metavar="KEY",
        help=(
            "Wrapper keys hidden in compact mode "
            "(default: children items)"
        ),
    )

    # --------------------------------------------------------
    # Tree -> JSON
    # --------------------------------------------------------

    ascii_parser = subparsers.add_parser(
        "ascii2json",
        help="Convert a reversible tree back to JSON",
    )

    ascii_parser.add_argument(
        "input",
        help="Input tree file, or '-' for stdin",
    )

    ascii_parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file",
    )

    ascii_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)",
    )

    ascii_parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help=(
            "Also print the formatted JSON in the terminal "
            "when -o is used"
        ),
    )

    args = parser.parse_args()

    # ========================================================
    # JSON -> tree
    # ========================================================

    if args.command == "json2ascii":

        json_text = read_text(args.input)
        data = json.loads(json_text)

        ascii_tree = json_to_tree(
            data,
            pretty=False,
        )

        # Save reversible ASCII if requested.
        if args.output:
            write_text(
                ascii_tree,
                args.output,
            )

        # Terminal display mode.
        if args.compact:

            print(
                json_to_compact_tree(
                    data,
                    label_keys=tuple(args.label_keys),
                    skip_keys=tuple(args.skip_keys),
                )
            )

        elif args.pretty:

            print(
                json_to_tree(
                    data,
                    pretty=True,
                )
            )

        elif not args.output:

            print(ascii_tree)

        else:

            print(
                f"Saved reversible ASCII tree to: "
                f"{args.output}"
            )

    # ========================================================
    # Tree -> JSON
    # ========================================================

    elif args.command == "ascii2json":

        tree_text = read_text(args.input)
        data = tree_to_json(tree_text)

        json_text = json.dumps(
            data,
            indent=args.indent,
            ensure_ascii=False,
        )

        if args.output:

            write_text(
                json_text,
                args.output,
            )

            if args.pretty:
                print(json_text)
            else:
                print(
                    f"Saved JSON to: {args.output}"
                )

        else:
            print(json_text)


if __name__ == "__main__":
    main()
