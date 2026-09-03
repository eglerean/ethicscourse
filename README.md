# JSON ↔ ASCII Tree Converter

A small command-line tool for converting JSON structures into readable tree output and converting the tree format back into JSON.

The script is assumed to be named:

```text
json_ascii_tree.py
```

## Requirements

Python 3 only. No external packages are required.

Check Python with:

```bash
python3 --version
```

## Quick start

### JSON → plain ASCII tree

Print the tree in the terminal:

```bash
python3 json_ascii_tree.py json2ascii data.json
```

Example output:

```text
<root>: {}
|-- "name": "Alice"
|-- "active": true
|-- "skills": []
|   |-- [0]: "R"
|   `-- [1]: "Python"
`-- "metadata": {}
    |-- "age": 30
    `-- "country": "Finland"
```

### JSON → pretty terminal tree

Use `--pretty` or `-p`:

```bash
python3 json_ascii_tree.py json2ascii data.json --pretty
```

or:

```bash
python3 json_ascii_tree.py json2ascii data.json -p
```

Example:

```text
<root>: {}
├── "name": "Alice"
├── "active": true
├── "skills": []
│   ├── [0]: "R"
│   └── [1]: "Python"
└── "metadata": {}
    ├── "age": 30
    └── "country": "Finland"
```

## Save the ASCII tree to a file

```bash
python3 json_ascii_tree.py json2ascii data.json -o data.tree
```

This saves the reversible plain-ASCII representation in `data.tree`.

## Save ASCII and also show the pretty tree

This is probably the most useful command:

```bash
python3 json_ascii_tree.py json2ascii data.json -o data.tree --pretty
```

It:

1. saves the reversible ASCII tree to `data.tree`;
2. prints the nicer Unicode tree in the terminal.

## ASCII tree → JSON

Convert a saved tree back to JSON:

```bash
python3 json_ascii_tree.py ascii2json data.tree -o reconstructed.json
```

The converter accepts both the plain ASCII tree and the pretty Unicode tree format.

## ASCII tree → JSON and print the JSON too

```bash
python3 json_ascii_tree.py ascii2json data.tree -o reconstructed.json --pretty
```

This saves `reconstructed.json` and also prints the formatted JSON in the terminal.

## Change JSON indentation

The default JSON indentation is 2 spaces.

For 4 spaces:

```bash
python3 json_ascii_tree.py ascii2json data.tree -o reconstructed.json --indent 4
```

## Use stdin / pipes

Use `-` instead of a filename to read from standard input.

For example:

```bash
cat data.json | python3 json_ascii_tree.py json2ascii - --pretty
```

## Command summary

```text
JSON → terminal ASCII
python3 json_ascii_tree.py json2ascii data.json

JSON → pretty terminal tree
python3 json_ascii_tree.py json2ascii data.json -p

JSON → saved ASCII tree
python3 json_ascii_tree.py json2ascii data.json -o data.tree

JSON → saved ASCII + pretty terminal output
python3 json_ascii_tree.py json2ascii data.json -o data.tree -p

ASCII → JSON
python3 json_ascii_tree.py ascii2json data.tree -o data.json

ASCII → JSON + print formatted JSON
python3 json_ascii_tree.py ascii2json data.tree -o data.json -p
```

## Notes

The tree format is intentionally explicit so that conversion is reversible.

It preserves:

- dictionaries / JSON objects;
- lists / arrays;
- strings;
- numbers;
- booleans;
- `null`;
- empty objects `{}`;
- empty arrays `[]`.

Dictionary keys remain JSON-quoted, and list elements are represented using indices such as `[0]`, `[1]`, etc.

## Help

To see the available commands:

```bash
python3 json_ascii_tree.py --help
```

For help on a specific conversion:

```bash
python3 json_ascii_tree.py json2ascii --help
```

or:

```bash
python3 json_ascii_tree.py ascii2json --help
```
