"""Low-level Endless Sky data-file parsing helpers.

These functions know nothing about the UI; they only turn the game's
tab-indented text data into Python structures.
"""

import os


def tokenize(line):
    """Split a data-file line into tokens, honoring quoted strings.

    Endless Sky uses double quotes for most strings and backticks when a
    string itself needs to contain double quotes.
    """
    tokens = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c in " \t":
            i += 1
            continue
        if c in ('"', '`'):
            quote = c
            j = i + 1
            while j < n and line[j] != quote:
                j += 1
            tokens.append(line[i + 1:j])
            i = j + 1
        else:
            j = i
            while j < n and line[j] not in " \t":
                j += 1
            tokens.append(line[i:j])
            i = j
    return tokens


def indent(line):
    """Return the tab indentation level of a line."""
    return len(line) - len(line.lstrip("\t"))


def parse_value(token):
    """Return the token as a float when possible, otherwise as a string."""
    try:
        return float(token)
    except ValueError:
        return token


def number(attrs, key):
    """Get a numeric attribute, defaulting to zero."""
    value = attrs.get(key, 0.0)
    return value if isinstance(value, float) else 0.0


def append_description(attrs, value):
    """Append one description line, joining paragraphs with a newline."""
    text = value.strip() if isinstance(value, str) else str(value)
    previous = attrs.get("description", "")
    attrs["description"] = text if not previous else previous + "\n" + text


def data_files(data_dir):
    """Yield the data files to scan, skipping the deprecated folder."""
    for root, dirs, files in os.walk(data_dir):
        if os.path.basename(root) == "_deprecated":
            continue
        for name in sorted(files):
            if name.endswith(".txt"):
                yield os.path.join(root, name)


def parse_blocks(data_dir):
    """Parse all ship definitions into base/variant blocks with attribute ops."""
    blocks = []
    for path in data_files(data_dir):
        faction = os.path.basename(os.path.dirname(path))
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            level = indent(line)
            tokens = tokenize(line)

            if level == 0 and len(tokens) >= 2 and tokens[0] == "ship":
                base = tokens[1]
                variant = tokens[2] if len(tokens) >= 3 else None
                ops = []
                descriptions = []
                i += 1

                # Consume this ship's block (all lines indented under it).
                while i < n and indent(lines[i]) > 0:
                    inner_level = indent(lines[i])
                    inner = tokenize(lines[i])

                    if inner_level == 1 and inner:
                        if inner[0] == "description" and len(inner) >= 2:
                            descriptions.append(inner[1].strip())
                            i += 1
                            continue
                        if inner[0] in ("sprite", "thumbnail", "display name", "plural") and len(inner) >= 2:
                            ops.append(("set", {inner[0]: inner[1]}))
                            i += 1
                            continue

                        if inner[0] == "attributes":
                            values = {}
                            ops.append(("set", values))
                            i += 1
                            while i < n and indent(lines[i]) > 1:
                                attr_level = indent(lines[i])
                                attr = tokenize(lines[i])
                                if attr_level == 2 and len(attr) >= 2:
                                    values[attr[0]] = parse_value(attr[1])
                                i += 1
                            continue

                        if inner[0] == "add" and len(inner) >= 2 and inner[1] == "attributes":
                            values = {}
                            ops.append(("add", values))
                            i += 1
                            while i < n and indent(lines[i]) > 1:
                                attr_level = indent(lines[i])
                                attr = tokenize(lines[i])
                                if attr_level == 2 and len(attr) >= 2:
                                    values[attr[0]] = parse_value(attr[1])
                                i += 1
                            continue

                    i += 1

                if descriptions:
                    ops.append(("set", {"description": "\n".join(descriptions)}))

                blocks.append({"base": base, "variant": variant,
                               "ops": ops, "faction": faction})
            else:
                i += 1

    return blocks


def parse_weapon_outfits(data_dir):
    """Parse every top-level outfit, capturing the nested weapon block.

    The weapon block holds the actual combat stats (damage, reload, range,
    etc.), which the generic outfit parser does not collect.
    """
    outfits = []
    for path in data_files(data_dir):
        faction = os.path.basename(os.path.dirname(path))
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()

        i = 0
        n = len(lines)
        while i < n:
            level = indent(lines[i])
            tokens = tokenize(lines[i])

            if level == 0 and len(tokens) >= 2 and tokens[0] == "outfit":
                name = tokens[1]
                attrs = {}
                weapon = {}
                i += 1
                while i < n and indent(lines[i]) > 0:
                    depth = indent(lines[i])
                    fields = tokenize(lines[i])
                    if depth == 1 and fields and fields[0] == "weapon":
                        i += 1
                        while i < n and indent(lines[i]) > 1:
                            if indent(lines[i]) == 2 and len(tokenize(lines[i])) >= 2:
                                w = tokenize(lines[i])
                                weapon[w[0]] = parse_value(w[1])
                            i += 1
                        continue
                    if depth == 1 and len(fields) >= 2:
                        if fields[0] == "description":
                            append_description(attrs, fields[1])
                        else:
                            attrs[fields[0]] = parse_value(fields[1])
                    i += 1

                attrs["weapon"] = weapon
                outfits.append({"name": name, "faction": faction, "attrs": attrs})
            else:
                i += 1

    return outfits
