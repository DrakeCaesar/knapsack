"""Ship data: bunk-capacity rows and variant deduplication."""

from .config import EXCLUDE_ZERO_COST
from .parse import number

# Outfit effects used by the ship bunks calculation.
EXPANSION_OUTFIT_SPACE = 15.0
EXPANSION_CARGO_SPACE = 20.0
BUNK_ROOM_BUNKS = 4.0
BUNK_ROOM_OUTFIT_SPACE = 20.0

# Ship bunks table columns: (header, row key, anchor). Column widths are not
# declared; each is auto-sized to the widest text in that column, including
# the header.
SHIP_COLUMNS = [
    ("Source Name", "name", "w"),
    ("In-Game Name", "display_name", "w"),
    ("Faction", "faction", "w"),
    ("Category", "category", "w"),
    ("Max Bunks", "max_bunks", "e"),
    ("Bunks", "bunks", "e"),
    ("Crew", "crew", "e"),
    ("Cargo", "cargo", "e"),
    ("Expansions", "expansions", "e"),
    ("Bunk Rooms", "bunk_rooms", "e"),
    ("Outfit Total", "outfit_total", "e"),
    ("Outfit", "outfit", "e"),
    ("Leftover Outfit", "leftover_outfit", "e"),
    ("Cost", "cost", "e"),
    ("Shields", "shields", "e"),
    ("Hull", "hull", "e"),
]


def apply_ops(attrs, ops):
    """Apply a block's attribute operations to the given attribute dict."""
    for mode, values in ops:
        if mode == "set":
            attrs.update(values)
        else:  # "add"
            for key, value in values.items():
                if isinstance(value, float) and isinstance(attrs.get(key), float):
                    attrs[key] += value
                else:
                    attrs[key] = value


def resolve_ships(blocks):
    """Resolve bases first, then variants, returning name/attribute rows."""
    base_attrs = {}

    # Bases must exist before variants can inherit from them.
    for block in blocks:
        if block["variant"] is None:
            attrs = {}
            apply_ops(attrs, block["ops"])
            base_attrs[block["base"]] = attrs

    ships = []
    for block in blocks:
        attrs = {}
        if block["variant"] is not None:
            attrs = base_attrs.get(block["base"], {}).copy()
        apply_ops(attrs, block["ops"])

        name = block["variant"] if block["variant"] is not None else block["base"]
        ships.append({"name": name, "base": block["base"],
                      "variant": block["variant"], "attrs": attrs,
                      "faction": block["faction"]})

    return ships


def build_rows(ships):
    """Compute the derived columns for every ship."""
    rows = []
    for ship in ships:
        attrs = ship["attrs"]
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        cargo = max(0.0, number(attrs, "cargo space"))
        outfit = max(0.0, number(attrs, "outfit space"))
        bunks = max(0.0, number(attrs, "bunks"))

        expansions = int(cargo // EXPANSION_CARGO_SPACE)
        outfit_total = outfit + expansions * EXPANSION_OUTFIT_SPACE
        bunk_rooms = int(outfit_total // BUNK_ROOM_OUTFIT_SPACE)
        max_bunks = bunks + bunk_rooms * BUNK_ROOM_BUNKS

        category = attrs.get("category", "")
        sprite = attrs.get("sprite", "")
        thumbnail = attrs.get("thumbnail", "")
        display_name = attrs.get("display name", "")
        if not isinstance(display_name, str) or not display_name:
            display_name = ship["base"] if ship["variant"] is not None else ship["name"]
        description = attrs.get("description", "")
        rows.append({
            "name": ship["name"],
            "display_name": display_name,
            "description": description if isinstance(description, str) else "",
            "is_base": ship["variant"] is None,
            "faction": ship["faction"],
            "category": category if isinstance(category, str) else "",
            "cost": cost,
            "shields": number(attrs, "shields"),
            "hull": number(attrs, "hull"),
            "crew": number(attrs, "required crew"),
            "bunks": bunks,
            "cargo": cargo,
            "outfit": outfit,
            "expansions": expansions,
            "outfit_total": outfit_total,
            "bunk_rooms": bunk_rooms,
            "max_bunks": max_bunks,
            "leftover_outfit": outfit_total - bunk_rooms * BUNK_ROOM_OUTFIT_SPACE,
            "sprite": sprite if isinstance(sprite, str) else "",
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["max_bunks"], row["name"].lower()))
    return rows


def dedupe_rows(rows):
    """Merge rows whose displayed table columns are identical.

    The table ignores loadouts and also hides some attributes (drag, fuel,
    weapon/engine capacity, mass, etc.), so ships that differ only in those
    hidden stats are still considered the same ship here. The merged row keeps
    the base ship's name (or the alphabetically first variant name when the
    group only contains variants).
    """
    key_columns = [key for _, key, _ in SHIP_COLUMNS if key != "name"]

    groups = {}
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        groups.setdefault(key, []).append(row)

    merged = []
    for group in groups.values():
        representative = None
        for row in group:
            if row.get("is_base"):
                representative = row
                break
        if representative is None:
            representative = min(group, key=lambda row: row["name"])
        merged.append(dict(representative))

    return merged
