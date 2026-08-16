#!/usr/bin/env python3
"""Pick the best engine combinations for a given ship engine capacity.

This is a Python reimplementation of the old ``knapsack`` project, but it reads
engine definitions directly from the game's data files instead of using the
hardcoded (and possibly outdated) values in ``values.txt`` / ``weights.txt``.

Model
-----
A ship has a single pool of engine capacity. That capacity is split between
thrusters (outfits with a ``"thrust"`` attribute) and steering (outfits with a
``"turn"`` attribute). For every possible split the script solves an unbounded
knapsack to maximize thrust in the thruster pool and turn in the steering pool,
then prints the Pareto frontier of (thrust, turn) results.

Usage
-----
    python engine_knapsack.py [capacity] [filter ...]

Examples
--------
    python engine_knapsack.py 180
    python engine_knapsack.py 180 human hai
    python engine_knapsack.py 120 korath
"""

import argparse
import os


def tokenize(line):
    """Split a data-file line into tokens, honoring quoted and backtick strings."""
    tokens = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c in " \t":
            i += 1
            continue
        if c == '"' or c == '`':
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


def data_files(data_dir):
    """Yield data files to scan, skipping the deprecated folder."""
    for root, dirs, files in os.walk(data_dir):
        if os.path.basename(root) == "_deprecated":
            continue
        for name in sorted(files):
            if name.endswith(".txt"):
                yield os.path.join(root, name)


def parse_outfits(data_dir):
    """Parse every top-level ``outfit`` block and return its scalar attributes."""
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
                i += 1
                # Consume this outfit's block; scalar attributes are at depth 1.
                while i < n and indent(lines[i]) > 0:
                    depth = indent(lines[i])
                    fields = tokenize(lines[i])
                    if depth == 1 and len(fields) >= 2:
                        attrs[fields[0]] = parse_value(fields[1])
                    i += 1
                outfits.append({"name": name, "faction": faction, "attrs": attrs})
            else:
                i += 1

    return outfits


def engine_weight(attrs):
    """Return the outfit space an engine consumes, as a positive integer."""
    for key in ("engine capacity", "outfit space"):
        value = attrs.get(key)
        if isinstance(value, float):
            return int(round(-value))
    return 0


def build_engines(outfits, filters):
    """Return a list of engine dicts: weight, thrust, turn, name, faction."""
    engines = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        thrust = attrs.get("thrust")
        turn = attrs.get("turn")
        if not isinstance(thrust, float) and not isinstance(turn, float):
            continue

        weight = engine_weight(attrs)
        if weight <= 0:
            continue

        # Filters match the outfit name, its faction folder, series, or category.
        blob = "{} {} {} {}".format(
            outfit["name"], outfit["faction"],
            attrs.get("series", ""), attrs.get("category", "")
        ).lower()
        if filters and "all" not in filters and not any(f in blob for f in filters):
            continue

        engines.append({
            "weight": weight,
            "thrust": thrust if isinstance(thrust, float) else 0.0,
            "turn": turn if isinstance(turn, float) else 0.0,
            "name": outfit["name"],
            "faction": outfit["faction"],
            "thumbnail": attrs.get("thumbnail", ""),
        })

    return engines


def prune_engines(engines):
    """Remove engines that are strictly worse than another in every dimension."""
    kept = []
    for engine in engines:
        dominated = False
        for other in kept:
            if (other["weight"] <= engine["weight"]
                    and other["thrust"] >= engine["thrust"]
                    and other["turn"] >= engine["turn"]
                    and (other["weight"] < engine["weight"]
                         or other["thrust"] > engine["thrust"]
                         or other["turn"] > engine["turn"])):
                dominated = True
                break
        if dominated:
            continue

        # Drop previously kept engines that this one dominates.
        kept = [other for other in kept if not (
            engine["weight"] <= other["weight"]
            and engine["thrust"] >= other["thrust"]
            and engine["turn"] >= other["turn"]
            and (engine["weight"] < other["weight"]
                 or engine["thrust"] > other["thrust"]
                 or engine["turn"] > other["turn"]))]
        kept.append(engine)

    return kept


class _Node:
    """A Pareto point in the DP, with a provenance link for reconstruction."""
    __slots__ = ("thrust", "turn", "weight", "prev", "item")

    def __init__(self, thrust, turn, weight, prev=None, item=None):
        self.thrust = thrust
        self.turn = turn
        self.weight = weight
        self.prev = prev
        self.item = item


def _prune(candidates):
    """Keep only non-dominated candidates, preferring the lightest recipe."""
    # First collapse equal (thrust, turn) points, keeping the one that uses the
    # least engine capacity (so the most capacity is left over).
    best = {}
    for node in candidates:
        key = (round(node.thrust, 4), round(node.turn, 4))
        current = best.get(key)
        if current is None or node.weight < current.weight:
            best[key] = node

    # Sorting by thrust descending lets a single pass build the frontier: a
    # point survives only if its turn exceeds every turn seen so far (all of
    # which have greater or equal thrust).
    points = sorted(best.values(), key=lambda node: (-node.thrust, -node.turn))
    frontier = []
    max_turn = -1.0
    for node in points:
        if node.turn > max_turn:
            frontier.append(node)
            max_turn = node.turn

    return frontier


def compute_frontier(capacity, engines):
    """Exact bi-objective unbounded knapsack.

    Returns the Pareto frontier of (thrust, turn) achievable with a total
    engine weight of at most ``capacity``. Every engine is a single item that
    contributes both values, so dual-purpose engines (e.g. the X1050) are
    handled correctly instead of being split into two pools.
    """
    base = _Node(0.0, 0.0, 0)
    levels = [[base]]

    for c in range(1, capacity + 1):
        # Either use less than c capacity (carry the previous frontier), ...
        candidates = list(levels[c - 1])
        # ... or add one more copy of some engine to an optimal c - w solution.
        for item_index, engine in enumerate(engines):
            weight = engine["weight"]
            if weight <= c:
                for node in levels[c - weight]:
                    candidates.append(_Node(
                        node.thrust + engine["thrust"],
                        node.turn + engine["turn"],
                        node.weight + weight,
                        node,
                        item_index,
                    ))
        levels.append(_prune(candidates))

    return levels[capacity]


def _recipe(node, engines):
    """Expand a DP node back into per-engine counts."""
    counts = {}
    while node is not None and node.item is not None:
        engine = engines[node.item]
        key = (engine["name"], engine["faction"])
        if key in counts:
            counts[key][0] += 1
        else:
            counts[key] = [1, engine]
        node = node.prev
    return counts


def print_frontier(nodes, capacity, engines):
    """Print the Pareto frontier in a readable form."""
    print("Engine capacity: {}".format(capacity))
    print("Non-dominated (thrust, turn) combinations: {}\n".format(len(nodes)))

    for node in nodes:
        counts = _recipe(node, engines)
        print("-" * 70)
        print("Total thrust: {:.2f}   Total turn: {:.2f}".format(
            node.thrust, node.turn))
        print("Used: {}   Unused: {}".format(node.weight, capacity - node.weight))
        print()

        entries = sorted(counts.values(), key=lambda entry: -entry[1]["weight"])
        for count, engine in entries:
            print("  {:>2}x {}  ({})  weight {:>3}  thrust {:>7.2f}  turn {:>7.2f}".format(
                count, engine["name"], engine["faction"],
                engine["weight"], engine["thrust"], engine["turn"]))
        print()


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_data = os.path.normpath(os.path.join(script_dir, "..", "data"))

    parser = argparse.ArgumentParser(
        description="Pick the best engines for a ship engine capacity using game data."
    )
    parser.add_argument("capacity", nargs="?", type=int, default=180,
                        help="Ship engine capacity (default: 180).")
    parser.add_argument("filters", nargs="*",
                        help="Optional substrings matching name/faction/series/category, or 'all'.")
    parser.add_argument("--data", default=default_data,
                        help="Path to the game's data directory.")
    args = parser.parse_args()

    outfits = parse_outfits(args.data)
    filters = [f.lower() for f in args.filters]
    engines = build_engines(outfits, filters)

    if not engines:
        print("No matching engines found.")
        return

    engines = prune_engines(engines)
    capacity = max(0, args.capacity)
    frontier = compute_frontier(capacity, engines)
    print_frontier(frontier, capacity, engines)


if __name__ == "__main__":
    main()
