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

# Responsible Research ontology viewer

An interactive, collapsible d3 tree (`docs/index.html`) visualizing the
Responsible Research pedagogical ontology. It's a separate, related tool
built on the same tree-editing idea as the converter above.

## Files

- `tree.md` -- the source of truth. A hand-edited, indented tree (see
  the docstring of `tree_md_to_json.py` for the exact syntax).
- `tree_md_to_json.py` -- converts `tree.md` into `docs/tree.json`.
- `moodle_to_leaf_json.py` -- builds `docs/leaf_content.json` from the
  Moodle pages in `moodle_data/` plus `extra_leaf_content.json`.
- `extra_leaf_content.json` -- hand-written side-panel links for topics
  with no Moodle page (`X2.1`, `X3.1`, ...) or extra links for ones
  that have one.
- `docs/tree.json`, `docs/leaf_content.json` -- generated output, loaded
  by the viewer at runtime. Do not edit by hand.
- `docs/index.html` -- the viewer, plus the triage checklist and the
  glossary below the map. It `fetch()`es the JSON files, so it must be
  served over HTTP, not opened directly as a `file://` URL (browsers
  block local `fetch()` for security; the page will show an on-screen
  message if this happens).

## Editing the ontology

1. Edit `tree.md`.

2. Regenerate `tree.json`:

   ```bash
   python3 tree_md_to_json.py tree.md -o docs/tree.json
   ```

3. Serve this folder and open the viewer in a browser:

   ```bash
   python3 -m http.server 8000 -d docs
   ```

   then visit `http://localhost:8000/`.

## Adding a link to a node

Any trailing parenthetical on a `tree.md` line -- `(3)`, `(link)`,
`(missing)`, etc. -- is kept as-is, as part of the node's name; it's
not split into separate JSON fields. Two of these are recognized by
the viewer as clickable at render time:

- `Node name (link)`, `(link?)`, `(link to ...)` -- a placeholder with
  no URL yet. Renders as clickable, but points at `#`.
- `Node name ([link](https://example.com))` -- a real URL, using
  Markdown link syntax. Renders as `Node name (link)`, clickable,
  opening `https://example.com`.

To turn a placeholder into a real link, replace it with the Markdown
form once you have the URL, e.g.:

```text
├── Fundamental rights (link)
```

becomes

```text
├── Fundamental rights ([link](https://www.finlex.fi/en/laws/...))
```

Then regenerate `tree.json` (step 2 above) and reload the page.

## Topic links and references (side panel)

Clicking the label of a numbered topic, e.g. `Ethical thinking (1.1)`
or `Fundamental rights (X3.1)`,
opens a card in the right-hand panel with that course section's links
and references. Clicking a node's circle still expands or collapses
its branch.

The cards come from `docs/leaf_content.json`, which is generated from
the Moodle pages in `moodle_data/` (`1.1.html`, `3.html`, ...) and the
hand-written `extra_leaf_content.json`. Video links are left out:

```bash
python3 moodle_to_leaf_json.py moodle_data docs/leaf_content.json
```

The output is rebuilt from scratch on every run, so never edit
`docs/leaf_content.json` by hand. Topics with no matching entry show
"will be added soon". To add one, either add a `moodle_data/N.M.html`
page, or put an entry under its key in `extra_leaf_content.json` and
regenerate. Keys are the trailing parenthetical of the node name: a
course section number (`6.5`) or one letter plus a number for extra
topics outside the course (`X3.1`). If the key also has a Moodle page,
extra items are added under the Moodle section with the same heading,
or as a new section after the Moodle ones:

```json
"6.5": {
  "sections": [
    { "heading": "Further reading", "items": [
      { "text": "Some article or book", "url": "https://..." },
      { "text": "A book without a link (Publisher, 2024)", "url": null }
    ] }
  ]
}
```
