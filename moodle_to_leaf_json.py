#!/usr/bin/env python3

"""
Extract the links and references from the Moodle course pages in
moodle_data/ into one JSON file that docs/index.html shows in its side
panel when a numbered topic of the mind map is clicked.

Only pages named after a course section are read -- "1.1.html",
"3.html" and so on. Everything else ("0_welcome.html", "1_intro.html",
the translation/ folder) is skipped.

Each page is split into blocks (paragraphs, list items, headings).
A heading, or a short paragraph that is entirely bold, starts a new
section ("Aalto support:", "Further reading and materials", ...). Every
non-empty block inside such a section becomes one item:

    { "text": "Beauchamp, T.L. & Childress ...", "url": null }
    { "text": "CRediT taxonomy", "url": "https://credit.niso.org/" }

Links that appear in the body text before the first section heading
are collected into a "Links" section. "Learning goal" sections are
skipped. Video links (iframes, YouTube, Vimeo, Panopto) are ignored.

The output looks like:

    {
      "1.1": {
        "sections": [
          { "heading": "Aalto support", "items": [ ... ] },
          { "heading": "Further reading and materials", "items": [ ... ] }
        ]
      }
    }

The output file is regenerated from scratch on every run, so do not
edit it by hand. Hand-written content goes in extra_leaf_content.json
next to this script, in the same format, and is merged into the output:
keys without a Moodle page ("X3.1", ...) are added as they are, and for
a key that has one, extra items go under the Moodle section with the
same heading, or into a new section after the Moodle ones.
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


# ============================================================
# Settings
# ============================================================

SECTION_FILE_RE = re.compile(r"^\d+(?:\.\d+)?\.html$")

VIDEO_URL_RE = re.compile(r"youtube\.com|youtu\.be|vimeo|panopto", re.I)

BLOCK_TAGS = {"p", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6"}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

SKIP_TAGS = {"iframe", "script", "style", "video"}

BOLD_TAGS = {"strong", "b"}

WEB_URL_RE = re.compile(r"^https?://", re.I)

SKIPPED_SECTION_RE = re.compile(r"^(learning goals?|pictures?|images?)$", re.I)

# Headings that introduce links or references. Any other bold
# subheading ("Open access publishing", ...) introduces course prose,
# from which only the links are kept.
RESOURCE_SECTION_RE = re.compile(
    r"support|reading|resource|material|link|reference|literature", re.I
)

# A bold paragraph longer than this is emphasised text, not a heading.
MAX_HEADING_LENGTH = 80

# Longest block whose whole text is used as the label of its one link.
MAX_LABEL_LENGTH = 250

SKIP = object()


# ============================================================
# HTML parsing
# ============================================================

def collapse(text):
    text = text.replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


class BlockParser(HTMLParser):
    """
    Flatten a Moodle page into a list of blocks:

        { "tag": "p", "text": "...", "bold": bool, "links": [(text, href)] }

    "bold" is True when every visible character of the block sits
    inside <strong>/<b>. Nested blocks (a <p> inside an <li>) simply
    end the outer block early -- Moodle's Word-pasted markup is too
    irregular for anything stricter to be worth it.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.current = None
        self.skip_depth = 0
        self.bold_depth = 0
        self.anchor = None

    def start_block(self, tag):
        self.flush()
        self.current = {
            "tag": tag,
            "parts": [],
            "bold_chars": 0,
            "plain_chars": 0,
            "links": [],
        }

    def flush(self):
        if self.current is None:
            return

        block = self.current
        self.current = None

        text = collapse("".join(block["parts"]))

        if not text and not block["links"]:
            return

        self.blocks.append({
            "tag": block["tag"],
            "text": text,
            "bold": block["bold_chars"] > 0 and block["plain_chars"] == 0,
            "links": [(collapse(t), href) for t, href in block["links"]],
        })

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return

        if tag in BLOCK_TAGS:
            self.start_block(tag)
        elif tag in BOLD_TAGS:
            self.bold_depth += 1
        elif tag == "a":
            href = dict(attrs).get("href")
            self.anchor = {"href": href, "parts": []} if href else None
        elif tag == "br" and self.current is not None:
            self.current["parts"].append(" ")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return

        if tag in BLOCK_TAGS:
            self.flush()
        elif tag in BOLD_TAGS:
            self.bold_depth = max(0, self.bold_depth - 1)
        elif tag == "a" and self.anchor is not None:
            if self.current is None:
                self.start_block("p")

            text = "".join(self.anchor["parts"])
            href = self.anchor["href"]
            links = self.current["links"]

            # Word-pasted titles are often split into one <a> per word,
            # all with the same href -- join them back into one link.
            if links and links[-1][1] == href:
                text = links[-1][0] + text
                links.pop()

            links.append((text, href))
            self.anchor = None

    def handle_data(self, data):
        if self.skip_depth:
            return

        if self.current is None:
            if not data.strip():
                return
            self.start_block("p")

        self.current["parts"].append(data)

        if self.anchor is not None:
            self.anchor["parts"].append(data)

        visible = len(data.strip())

        if self.bold_depth:
            self.current["bold_chars"] += visible
        else:
            self.current["plain_chars"] += visible

    def close(self):
        super().close()
        self.flush()


# ============================================================
# Blocks -> sections
# ============================================================

def is_heading(block):
    if block["tag"] in HEADING_TAGS:
        return True

    if SKIPPED_SECTION_RE.match(clean_heading(block["text"])):
        return True

    return (
        block["bold"]
        and not block["links"]
        and len(block["text"]) <= MAX_HEADING_LENGTH
    )


def clean_heading(text):
    return collapse(text).rstrip(" :").strip()


def clean_item(text):
    text = collapse(text).lstrip("•·-– ").strip()
    text = re.sub(r"\|(\s*\|)+", "|", text)
    return re.sub(r"(\s*\|)+$", "", text).strip()


def is_url_text(text):
    """A block whose text is just a URL, or a wrapped piece of one."""
    return " " not in text and (
        text.startswith(("http", "/", "www."))
        or text.endswith((".pdf", ".html", ".htm"))
    )


def extract_sections(html):
    parser = BlockParser()
    parser.feed(html)
    parser.close()

    sections = []
    # None = links-only mode (body text before the first heading, or
    # a content subheading such as "Open access publishing"), SKIP =
    # inside a skipped section, otherwise a resource section heading.
    current = None

    def section(heading):
        for existing in sections:
            if existing["heading"] == heading:
                return existing

        new = {"heading": heading, "items": []}
        sections.append(new)
        return new

    for block in parser.blocks:

        links = [
            (text, href) for text, href in block["links"]
            if WEB_URL_RE.match(href) and not VIDEO_URL_RE.search(href)
        ]

        if is_heading(block):
            heading = clean_heading(block["text"])

            if not heading:
                continue

            if SKIPPED_SECTION_RE.match(heading):
                current = SKIP
            elif RESOURCE_SECTION_RE.search(heading):
                current = heading
            else:
                current = None
            continue

        if current is SKIP:
            continue

        if current is None:
            # Prose: keep only its links. A short block holding a single
            # link is a reference line, so its full text is the label.
            if len(links) == 1 and len(block["text"]) <= MAX_LABEL_LENGTH:
                links = [(block["text"], links[0][1])]

            for text, href in links:
                section("Links")["items"].append(
                    {"text": clean_item(text) or href, "url": href}
                )
            continue

        if block["links"] and not links:
            # The block was only a video or local-file link.
            continue

        text = clean_item(block["text"])

        if not text:
            continue

        items = section(current)["items"]
        previous = items[-1] if items else None
        url = links[0][1] if links else None

        if previous and is_url_text(text):
            # Word-pasted references often put the title on one line
            # and its URL (sometimes wrapped over several) on the next.
            if previous["url"] is None:
                previous["url"] = url
            continue

        if previous and previous["url"] is None and text[0].islower():
            # Continuation of a title that wrapped onto a new line.
            previous["text"] += " " + text
            previous["url"] = url
            continue

        items.append({"text": text, "url": url})

    return dedupe(sections)


def dedupe(sections):
    """
    Drop repeated URLs. A link that appears both in the body text and
    under a resource heading is kept only under the heading.
    """
    listed = {
        item["url"]
        for s in sections if s["heading"] != "Links"
        for item in s["items"] if item["url"]
    }

    result = []

    for s in sections:
        seen = set()
        items = []

        for item in s["items"]:
            url = item["url"]

            if url and (url in seen or (s["heading"] == "Links" and url in listed)):
                continue

            seen.add(url)
            items.append(item)

        if items:
            result.append({"heading": s["heading"], "items": items})

    return result


# ============================================================
# Main
# ============================================================

def section_key(path):
    return [int(part) for part in path.stem.split(".")]


def load_extra(path):
    """Hand-written entries, or {} if the file does not exist."""
    if not path.is_file():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        sys.exit(f"Invalid JSON in {path}: {error}")


def merge_extra(result, extra):
    for key, entry in extra.items():
        sections = result.setdefault(key, {"sections": []})["sections"]

        for extra_section in entry.get("sections", []):
            same = [s for s in sections
                    if s["heading"] == extra_section["heading"]]

            if same:
                same[0]["items"].extend(extra_section["items"])
            else:
                sections.append(extra_section)


def main():
    parser = argparse.ArgumentParser(
        description="Extract links and references from Moodle pages "
                    "into JSON for the mind map's side panel."
    )
    parser.add_argument("input_dir", help="folder with N.M.html pages")
    parser.add_argument("output", help="JSON file to write, or - for stdout")
    parser.add_argument(
        "--extra",
        default=Path(__file__).resolve().parent / "extra_leaf_content.json",
        type=Path,
        help="hand-written entries to merge in "
             "(default: extra_leaf_content.json next to this script)",
    )
    args = parser.parse_args()

    pages = sorted(
        (p for p in Path(args.input_dir).iterdir()
         if p.is_file() and SECTION_FILE_RE.match(p.name)),
        key=section_key,
    )

    result = {}

    for page in pages:
        sections = extract_sections(page.read_text(encoding="utf-8"))

        if sections:
            result[page.stem] = {"sections": sections}

    extra = load_extra(args.extra)
    merge_extra(result, extra)

    if extra:
        print(f"Merged {len(extra)} extra entries from {args.extra}",
              file=sys.stderr)

    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"

    if args.output == "-":
        sys.stdout.write(output)
    else:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {len(result)} sections to {args.output}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
