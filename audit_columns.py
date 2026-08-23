#!/usr/bin/env python3
"""Audit the comparison tabs for missing columns.

Two checks are performed for every tab/category:

1. Completeness: every defined column key must be populated in every row
   (catches a column defined in the table but never filled by its builder).
2. Missing stats: numeric attributes that exist in the game data but are not
   shown as any column (useful when adding new stats).

Run from the repository root (or anywhere):

    python knapsack/audit_columns.py

No Qt/GUI is required; this only uses the pure-Python data builders.
"""

import os
import sys

KNAPSACK_DIR = os.path.dirname(os.path.abspath(__file__))
if KNAPSACK_DIR not in sys.path:
    sys.path.insert(0, KNAPSACK_DIR)

from es_tools import outfits as O
from es_tools.parse import shared_blocks, shared_outfits, shared_weapons
from es_tools.ships import SHIP_COLUMNS, build_rows, resolve_ships

# Attributes that are bookkeeping/identifying, not comparable stats.
META = {"name", "faction", "series", "category", "description", "thumbnail",
        "sprite", "index", "cost", "mass"}

# Boolean/tag/narrative values, not numeric stats worth a column.
FLAGS = {
    "unique", "unplunderable", "illegal", "inscrutable", "installable",
    "map", "map minables", "anchor point", "shooting star", "core crystal",
    "drill spar", "drill port", "drill lock", "automaton", "self destruct",
    "cloak", "cloak phasing", "silent jumps", "cloaked firing",
    "cloaked communication", "cloaked scanning",
    "cloaked shield permeability", "remnant node", "gaslining", "waterlining",
    "ka'sei", "exclusive: Vujlet", "#",
}

# Raw attribute name -> row key(s) it feeds. A stat counts as "shown" if any
# candidate key appears in the column set (handles derived/renamed columns).
DERIVED = {
    "outfit space": ("space",),
    "cargo space": ("cargo",),
    "cargo capacity": ("cargo",),
    "engine capacity": ("space", "engine_capacity"),
    "weapon capacity": ("space", "weapon_capacity"),
    "required crew": ("crew",),
    "crew equivalent": ("crew",),
    "thrusting energy": ("energy",),
    "turning energy": ("energy",),
    "afterburner energy": ("energy",),
    "reverse thrusting energy": ("energy",),
    "thrusting heat": ("heat",),
    "turning heat": ("heat",),
    "afterburner heat": ("heat",),
    "reverse thrusting heat": ("heat",),
    "energy generation": ("energy",),
    "heat generation": ("heat", "heat_generation"),
    "solar collection": ("solar",),
    "solar heat": ("solar_heat",),
    "hull repair rate": ("hull_repair",),
    "energy consumption": ("energy", "energy_consumption"),
    "energy capacity": ("energy_capacity",),
    "shield generation": ("shield_generation",),
    "radar jamming": ("jamming",),
    "tactical scan power": ("scan_power",),
    "capture attack": ("capture_attack",),
    "capture defense": ("capture_defense",),
    "fuel capacity": ("fuel_capacity",),
    "shield energy": ("shield_energy",),
    "shield heat": ("shield_heat",),
    "hull energy": ("hull_energy",),
    "hull heat": ("hull_heat",),
    "fuel generation": ("fuel_generation",),
    "hull repair multiplier": ("hull_repair_multiplier",),
    "cargo scan power": ("cargo_scan_power",),
    "outfit scan power": ("outfit_scan_power",),
    "asteroid scan power": ("asteroid_scan_power",),
    "scan interference": ("scan_interference",),
    "jump speed": ("jump_speed",),
    "jump fuel": ("jump_fuel",),
    "shield protection": ("shield_protection",),
    "hull protection": ("hull_protection",),
    "bunks": ("bunks",),
    "turret mounts": ("turret_mounts",),
    "gun ports": ("gun_ports",),
    "spinal mount": ("spinal_mount",),
    "heat capacity": ("heat_capacity",),
    "heat dissipation": ("heat_dissipation",),
    "active cooling": ("active_cooling",),
    "cooling energy": ("cooling_energy",),
    "afterburner thrust": ("afterburner_thrust",),
    "afterburner fuel": ("afterburner_fuel",),
    "afterburner shields": ("afterburner_shields",),
    "reverse thrust": ("reverse_thrust",),
    "thrusting fuel": ("thrusting_fuel",),
    "thrust": ("thrust",),
    "turn": ("turn",),
    "ramscoop": ("ramscoop",),
    "cooling": ("cooling",),
    "hull": ("hull",),
    "shields": ("shields",),
    "drag": ("drag",),
    "inertia reduction": ("inertia_reduction",),
    "force protection": ("force_protection",),
    "slowing resistance": ("slowing_resistance",),
    "ion resistance": ("ion_resistance",),
    "scramble resistance": ("scramble_resistance",),
    "shield energy multiplier": ("shield_energy_multiplier",),
    "hull energy multiplier": ("hull_energy_multiplier",),
    "flotsam chance": ("flotsam_chance",),
    "cloaking energy": ("cloaking_energy",),
    "cloaking fuel": ("cloaking_fuel",),
    "jump drive": ("etype",),
    "hyperdrive": ("etype",),
    "scram drive": ("etype",),
    "quantum keystone": ("etype",),
}

# Raw weapon-block attribute name -> weapon row key.
WEAPON_MAP = {
    "shield damage": "shield_damage",
    "hull damage": "hull_damage",
    "disabled damage": "disabled_damage",
    "minable damage": "minable_damage",
    "fuel damage": "fuel_damage",
    "heat damage": "heat_damage",
    "energy damage": "energy_damage",
    "ion damage": "ion_damage",
    "scrambling damage": "scrambling_damage",
    "disruption damage": "disruption_damage",
    "slowing damage": "slowing_damage",
    "discharge damage": "discharge_damage",
    "corrosion damage": "corrosion_damage",
    "leak damage": "leak_damage",
    "burn damage": "burn_damage",
    "piercing": "piercing",
    "hit force": "hit_force",
    "missile strength": "missile_strength",
    "blast radius": "blast_radius",
    "range": "range",
    "reload": "reload",
    "burst count": "burst_count",
    "burst reload": "burst_reload",
    "velocity": "velocity",
    "lifetime": "lifetime",
    "turn": "turn",
    "inaccuracy": "inaccuracy",
    "drag": "drag",
    "acceleration": "acceleration",
    "tracking": "tracking",
    "turret turn": "turret_turn",
    "firing energy": "energy",
    "firing heat": "heat",
    "firing fuel": "fuel",
    "firing force": "firing_force",
    "trigger radius": "trigger_radius",
    "split range": "split_range",
    "penetration count": "penetration_count",
    "damage dropoff": "damage_dropoff",
    "dropoff modifier": "dropoff_modifier",
    "random velocity": "random_velocity",
    "random lifetime": "random_lifetime",
    "prospecting": "prospecting",
    "firing hull": "firing_hull",
    "firing shields": "firing_shields",
}


def column_keys(columns):
    return {key for _, key, _ in columns}


def _covered(raw_key, shown):
    """True if a raw outfit attribute is a flag or feeds a shown column."""
    if raw_key in FLAGS:
        return True
    if any(cand in shown for cand in DERIVED.get(raw_key, (raw_key,))):
        return True
    # Newer columns are just the raw name with spaces -> underscores.
    return raw_key.replace(" ", "_") in shown


def check_complete(name, rows, columns):
    """Every defined column key must be present in every row."""
    keys = column_keys(columns)
    missing = set()
    for row in rows:
        missing |= keys - set(row.keys())
    status = "OK" if not missing else "MISSING: {}".format(sorted(missing))
    print("  [complete] {:<18} rows={:<4} cols={:<3} {}".format(
        name, len(rows), len(columns), status))


def check_missing_stats(name, outfits, predicate, columns, use_weapon=False):
    """Numeric stats present in the data but genuinely not shown as columns."""
    shown = column_keys(columns)
    missing = set()
    for outfit in outfits:
        attrs = outfit["attrs"]
        if not predicate(attrs):
            continue
        for key, value in attrs.items():
            if isinstance(value, (int, float)) and key not in META \
                    and key != "weapon" and not _covered(key, shown):
                missing.add(key)
        if use_weapon:
            for key, value in (attrs.get("weapon") or {}).items():
                if isinstance(value, (int, float)) \
                        and WEAPON_MAP.get(key, key.replace(" ", "_")) not in shown:
                    missing.add("weapon." + key)
    missing = sorted(missing)
    print("  [missing]  {:<18} {} stats not shown: {}".format(
        name, len(missing), missing or "none"))


def main():
    outfits = shared_outfits()
    weapons = shared_weapons()
    blocks = shared_blocks()

    print("== Column completeness ==")
    check_complete("engines", O.build_engine_rows(outfits), O.ENGINE_COLUMNS)
    check_complete("power", O.build_power_rows(outfits), O.POWER_COLUMNS)
    check_complete("systems", O.build_systems_rows(outfits), O.SYSTEMS_COLUMNS)
    check_complete("h2h", O.build_h2h_rows(outfits), O.H2H_COLUMNS)
    check_complete("adv engines", O.build_advanced_engine_rows(outfits),
                   O.ADV_ENGINE_COLUMNS)
    check_complete("unique/special", O.build_unique_rows(outfits),
                   O.UNIQUE_COLUMNS)
    check_complete("weapons", O.build_weapon_rows(weapons), O.WEAPON_COLUMNS)
    check_complete("ships", build_rows(resolve_ships(blocks)), SHIP_COLUMNS)

    print("\n== Stats present in data but not shown as columns ==")
    check_missing_stats("engines",
                        outfits, lambda a: a.get("series") in O.ENGINE_SERIES,
                        O.ENGINE_COLUMNS)
    check_missing_stats("power",
                        outfits, lambda a: a.get("series") in O.POWER_SERIES,
                        O.POWER_COLUMNS)
    check_missing_stats("systems",
                        outfits, lambda a: a.get("category") == "Systems",
                        O.SYSTEMS_COLUMNS)
    check_missing_stats("h2h", outfits, O.is_h2h, O.H2H_COLUMNS)
    check_missing_stats(
        "adv engines",
        outfits, lambda a: O.advanced_engine_type(a) is not None,
        O.ADV_ENGINE_COLUMNS)
    check_missing_stats(
        "unique/special",
        outfits, lambda a: a.get("category") in ("Unique", "Special")
        and not O.is_h2h(a), O.UNIQUE_COLUMNS)
    check_missing_stats(
        "weapons",
        weapons, lambda a: a.get("category")
        in ("Guns", "Turrets", "Secondary Weapons"), O.WEAPON_COLUMNS,
        use_weapon=True)

    # Ships use attribute ops (set/add) rather than a flat attrs dict.
    shown = column_keys(SHIP_COLUMNS)
    missing = set()
    for block in blocks:
        for _mode, values in block["ops"]:
            for key, value in values.items():
                if isinstance(value, (int, float)) and key not in META \
                        and not _covered(key, shown):
                    missing.add(key)
    missing = sorted(missing)
    print("  [missing]  {:<18} {} stats not shown: {}".format(
        "ships", len(missing), missing or "none"))


if __name__ == "__main__":
    main()
