"""Outfit data: generator, engine, and weapon row builders plus columns.

Each builder turns parsed outfits into comparable table rows. Column tuples
are (header, row key, anchor); widths are auto-sized by the table at runtime.
"""

import math

from .config import EXCLUDE_ZERO_COST
from .parse import number

# Generator comparison table columns: (header, row key, anchor). Column widths
# are auto-sized to the widest text in each column, including the header.
GENERATOR_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Energy/s", "energy", "e"),
    ("Heat/s", "heat", "e"),
    ("Energy/Space", "energy_per_space", "e"),
    ("Energy/Heat", "energy_per_heat", "e"),
]

# Engine comparison table columns: (header, row key, anchor). Column widths are
# auto-sized to the widest text in each column, including the header.
ENGINE_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Thrust", "thrust", "e"),
    ("Turn", "turn", "e"),
    ("Energy/s", "energy", "e"),
    ("Heat/s", "heat", "e"),
    ("Thrust/Space", "thrust_per_space", "e"),
    ("Turn/Space", "turn_per_space", "e"),
    ("Rev Thr", "reverse_thrust", "e"),
    ("Aft Thr", "afterburner_thrust", "e"),
    ("Aft Ht", "afterburner_heat", "e"),
    ("Aft Fuel", "afterburner_fuel", "e"),
    ("Weapon Cap", "weapon_capacity", "e"),
    ("Thrust Fuel", "thrusting_fuel", "e"),
]

# Weapon comparison table columns: (header, row key, anchor). Column widths are
# not declared; each is auto-sized to the widest text in that column, including
# the header. Damage columns are per shot; rates (En/s, Ht/s, Fuel/s, Reload,
# DPS) are normalized to a one-second firing cycle where applicable.
WEAPON_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Mount", "mount", "w"),
    ("Type", "type", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    # Direct damage.
    ("Shield", "shield_damage", "e"),
    ("Hull", "hull_damage", "e"),
    ("Disabl", "disabled_damage", "e"),
    ("Minabl", "minable_damage", "e"),
    ("Fuel Dmg", "fuel_damage", "e"),
    ("Heat Dmg", "heat_damage", "e"),
    ("En Dmg", "energy_damage", "e"),
    # Status damage.
    ("Ion", "ion_damage", "e"),
    ("Scrambl", "scrambling_damage", "e"),
    ("Disrupt", "disruption_damage", "e"),
    ("Slow", "slowing_damage", "e"),
    ("Dischrg", "discharge_damage", "e"),
    ("Corro", "corrosion_damage", "e"),
    ("Leak", "leak_damage", "e"),
    ("Burn", "burn_damage", "e"),
    # Other damage modifiers.
    ("Pierce", "piercing", "e"),
    ("HitForce", "hit_force", "e"),
    ("Missile", "missile_strength", "e"),
    ("BlastRad", "blast_radius", "e"),
    # Projectile mechanics.
    ("Range", "range", "e"),
    ("Reload", "reload", "e"),
    ("Burst", "burst_count", "e"),
    ("BurstRel", "burst_reload", "e"),
    ("DPS", "dps", "e"),
    ("Velocity", "velocity", "e"),
    ("Life", "lifetime", "e"),
    ("Turn", "turn", "e"),
    ("Inacc", "inaccuracy", "e"),
    ("Drag", "drag", "e"),
    ("Accel", "acceleration", "e"),
    ("Track", "tracking", "e"),
    ("T-Turn", "turret_turn", "e"),
    # Firing costs, per second.
    ("En/s", "energy", "e"),
    ("Ht/s", "heat", "e"),
    ("Fuel/s", "fuel", "e"),
    ("Force/s", "firing_force", "e"),
    # Niche mechanics.
    ("Trigger", "trigger_radius", "e"),
    ("Split", "split_range", "e"),
    ("Penetr", "penetration_count", "e"),
    ("Dropoff", "damage_dropoff", "e"),
    ("Drop Mod", "dropoff_modifier", "e"),
    ("Rand Vel", "random_velocity", "e"),
    ("Rand Life", "random_lifetime", "e"),
    ("Prospect", "prospecting", "e"),
    ("Fire Hull", "firing_hull", "e"),
    ("Fire Shield", "firing_shields", "e"),
    ("Fire Ion", "firing_ion", "e"),
    ("Fire Scram", "firing_scramble", "e"),
    ("Rel Fire Sh", "relative_firing_shields", "e"),
]


def build_generator_rows(outfits):
    """Return one row per generator outfit with comparable stats."""
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("series") != "Generators":
            continue

        energy = number(attrs, "energy generation")
        heat = number(attrs, "heat generation")
        space = max(0.0, -number(attrs, "outfit space"))
        mass = number(attrs, "mass")
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": mass,
            "space": space,
            "energy": energy,
            "heat": heat,
            "energy_per_space": energy / space if space > 0 else 0.0,
            "energy_per_heat": energy / heat if heat > 0 else 0.0,
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["energy"], row["name"].lower()))
    return rows


# Engine series handled by the Engines tab.
ENGINE_SERIES = {"Engines"}


def build_engine_rows(outfits, series=None):
    """Return one row per engine outfit with comparable stats.

    ``series`` optionally restricts the rows to a single engine series.
    """
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("series") not in ENGINE_SERIES:
            continue
        if series is not None and attrs.get("series") != series:
            continue

        thrust = number(attrs, "thrust")
        turn = number(attrs, "turn")
        if thrust == 0.0 and turn == 0.0:
            continue

        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        mass = number(attrs, "mass")
        space = max(0.0, -number(attrs, "outfit space"),
                    -number(attrs, "engine capacity"))
        energy = number(attrs, "thrusting energy") + number(attrs, "turning energy")
        heat = number(attrs, "thrusting heat") + number(attrs, "turning heat")
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": mass,
            "space": space,
            "thrust": thrust,
            "turn": turn,
            "energy": energy,
            "heat": heat,
            "thrust_per_space": thrust / space if space > 0 else 0.0,
            "turn_per_space": turn / space if space > 0 else 0.0,
            "reverse_thrust": number(attrs, "reverse thrust"),
            "afterburner_thrust": number(attrs, "afterburner thrust"),
            "afterburner_heat": number(attrs, "afterburner heat"),
            "afterburner_fuel": number(attrs, "afterburner fuel"),
            "weapon_capacity": max(0.0, number(attrs, "weapon capacity")),
            "thrusting_fuel": number(attrs, "thrusting fuel"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["thrust"], row["name"].lower()))
    return rows


def weapon_type(weapon):
    """Classify a weapon block into a display type for grouping.

    Priority order: point-defense, tractor beams, seeking weapons, then
    instant-hit beams, and finally ordinary projectile guns.
    """
    if number(weapon, "anti-missile") > 0:
        return "Anti-Missile"
    if number(weapon, "tractor beam") > 0:
        return "Tractor Beam"
    for key in ("homing", "tracking", "optical tracking",
                "infrared tracking", "radar tracking"):
        if key in weapon:
            return "Missile"
    if number(weapon, "lifetime") == 1.0:
        return "Beam"
    return "Projectile"


def build_weapon_rows(outfits, types=None, mount=None):
    """Return one row per player weapon outfit of the given type(s) and mount.

    ``types`` is a set of weapon_type() results, or None for all types.
    ``mount`` is a category ("Guns", "Turrets", "Secondary Weapons"), or None
    for all mounts.
    """
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        category = attrs.get("category", "")
        if category not in ("Guns", "Turrets", "Secondary Weapons"):
            continue
        if mount is not None and category != mount:
            continue
        weapon = attrs.get("weapon", {})
        if not weapon:
            continue
        wtype = weapon_type(weapon)
        if types is not None and wtype not in types:
            continue

        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        mass = number(attrs, "mass")
        space = max(0.0, -number(attrs, "outfit space"))

        shield = number(weapon, "shield damage")
        hull = number(weapon, "hull damage")
        disabled = number(weapon, "disabled damage") or hull
        minable = number(weapon, "minable damage") or hull
        fuel_dmg = number(weapon, "fuel damage")
        heat_dmg = number(weapon, "heat damage")
        energy_dmg = number(weapon, "energy damage")
        ion = number(weapon, "ion damage")
        scrambling = number(weapon, "scrambling damage")
        disruption = number(weapon, "disruption damage")
        slowing = number(weapon, "slowing damage")
        discharge = number(weapon, "discharge damage")
        corrosion = number(weapon, "corrosion damage")
        leak = number(weapon, "leak damage")
        burn = number(weapon, "burn damage")
        piercing = number(weapon, "piercing")
        hit_force = number(weapon, "hit force")
        missile_strength = number(weapon, "missile strength")
        blast_radius = number(weapon, "blast radius")

        velocity = number(weapon, "velocity")
        if velocity == 0:
            velocity = number(weapon, "velocity override")
        lifetime = number(weapon, "lifetime")
        rng = number(weapon, "range")
        if rng <= 0:
            rng = number(weapon, "range override")
        if rng <= 0 and velocity > 0 and lifetime > 0:
            rng = velocity * lifetime
        burst_count = max(1, int(number(weapon, "burst count") or 1))
        reload = max(0.001, number(weapon, "reload") / 60.0)
        raw_burst_reload = number(weapon, "burst reload")
        burst_reload = raw_burst_reload / 60.0 if raw_burst_reload > 0 else reload
        turn = number(weapon, "turn")
        inaccuracy = number(weapon, "inaccuracy")
        drag = number(weapon, "drag")
        acceleration = number(weapon, "acceleration")
        tracking = max(number(weapon, "tracking"),
                       number(weapon, "optical tracking"),
                       number(weapon, "infrared tracking"),
                       number(weapon, "radar tracking"))
        turret_turn = number(weapon, "turret turn")

        dps = (shield + hull) * burst_count / reload
        energy = number(weapon, "firing energy") * burst_count / reload
        heat = number(weapon, "firing heat") * burst_count / reload
        fuel = number(weapon, "firing fuel") * burst_count / reload
        firing_force = number(weapon, "firing force") * burst_count / reload
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "mount": category,
            "type": wtype,
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": mass,
            "space": space,
            "shield_damage": shield,
            "hull_damage": hull,
            "disabled_damage": disabled,
            "minable_damage": minable,
            "fuel_damage": fuel_dmg,
            "heat_damage": heat_dmg,
            "energy_damage": energy_dmg,
            "ion_damage": ion,
            "scrambling_damage": scrambling,
            "disruption_damage": disruption,
            "slowing_damage": slowing,
            "discharge_damage": discharge,
            "corrosion_damage": corrosion,
            "leak_damage": leak,
            "burn_damage": burn,
            "piercing": piercing,
            "hit_force": hit_force,
            "missile_strength": missile_strength,
            "blast_radius": blast_radius,
            "range": rng,
            "reload": reload,
            "burst_count": burst_count,
            "burst_reload": burst_reload,
            "dps": dps,
            "velocity": velocity,
            "lifetime": lifetime,
            "turn": turn,
            "inaccuracy": inaccuracy,
            "drag": drag,
            "acceleration": acceleration,
            "tracking": tracking,
            "turret_turn": turret_turn,
            "energy": energy,
            "heat": heat,
            "fuel": fuel,
            "firing_force": firing_force,
            "trigger_radius": number(weapon, "trigger radius"),
            "split_range": number(weapon, "split range"),
            "penetration_count": number(weapon, "penetration count"),
            "damage_dropoff": number(weapon, "damage dropoff"),
            "dropoff_modifier": number(weapon, "dropoff modifier"),
            "random_velocity": number(weapon, "random velocity"),
            "random_lifetime": number(weapon, "random lifetime"),
            "prospecting": number(weapon, "prospecting"),
            "firing_hull": number(weapon, "firing hull"),
            "firing_shields": number(weapon, "firing shields"),
            "firing_ion": number(weapon, "firing ion"),
            "firing_scramble": number(weapon, "firing scramble"),
            "relative_firing_shields": number(weapon, "relative firing shields"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["dps"], row["name"].lower()))
    return rows


def weapon_mount_types(outfits):
    """Return the ordered (mount, type) groups that actually contain weapons.

    Used to build the Weapons tab's nested structure - mount first, then the
    weapon type - so only tabs that really have weapons are created.
    """
    mounts = ["Guns", "Turrets", "Secondary Weapons"]
    type_order = ["Beam", "Projectile", "Missile", "Anti-Missile",
                  "Tractor Beam"]

    present = set()
    for outfit in outfits:
        attrs = outfit["attrs"]
        category = attrs.get("category", "")
        if category not in mounts:
            continue
        weapon = attrs.get("weapon", {})
        if not weapon:
            continue
        present.add((category, weapon_type(weapon)))

    groups = []
    for mount in mounts:
        for wtype in type_order:
            if (mount, wtype) in present:
                groups.append((mount, wtype))
    return groups


# Power outfit series handled by the Power tab (the game's "Power" category).
POWER_SERIES = {"Generators", "Batteries", "Solar"}

# Power comparison table columns: (header, row key, anchor).
POWER_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Type", "series", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Energy/s", "energy", "e"),
    ("En Cap", "energy_capacity", "e"),
    ("Heat/s", "heat", "e"),
    ("Energy/Space", "energy_per_space", "e"),
    ("Energy/Heat", "energy_per_heat", "e"),
    ("Solar", "solar", "e"),
    ("Solar Ht", "solar_heat", "e"),
    ("Ion Res", "ion_resistance", "e"),
    ("Scram Res", "scramble_resistance", "e"),
    ("Sh En x", "shield_energy_multiplier", "e"),
    ("Hull En x", "hull_energy_multiplier", "e"),
    ("En Use", "energy_consumption", "e"),
]

# Systems comparison table columns.
SYSTEMS_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Type", "series", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Shields", "shields", "e"),
    ("Sh Gen", "shield_generation", "e"),
    ("Cooling", "cooling", "e"),
    ("Scan", "scan_power", "e"),
    ("Repair", "hull_repair", "e"),
    ("Hull", "hull", "e"),
    ("Jam", "jamming", "e"),
    ("En Use", "energy", "e"),
    ("Fuel", "fuel_capacity", "e"),
    ("Ramscp", "ramscoop", "e"),
    ("Ramscoop/Space", "ramscoop_per_space", "e"),
    ("Eff Ramscp", "ramscoop_effective", "e"),
    ("Eff Ramscp/Space", "ramscoop_effective_per_space", "e"),
    # Power draw / production.
    ("Sh En", "shield_energy", "e"),
    ("Sh Ht", "shield_heat", "e"),
    ("Hull En", "hull_energy", "e"),
    ("Hull Ht", "hull_heat", "e"),
    ("Heat Gen", "heat_generation", "e"),
    ("En Cap", "energy_capacity", "e"),
    ("Active Cool", "active_cooling", "e"),
    ("Cool En", "cooling_energy", "e"),
    ("Fuel Gen", "fuel_generation", "e"),
    ("Repair x", "hull_repair_multiplier", "e"),
    # Scanning.
    ("Cargo Scan", "cargo_scan_power", "e"),
    ("Outfit Scan", "outfit_scan_power", "e"),
    ("Asteroid Scan", "asteroid_scan_power", "e"),
    ("Scan Interf", "scan_interference", "e"),
    # Mobility / capacity.
    ("Jump Spd", "jump_speed", "e"),
    ("Jump Fuel", "jump_fuel", "e"),
    ("Shield Prot", "shield_protection", "e"),
    ("Hull Prot", "hull_protection", "e"),
    ("Bunks", "bunks", "e"),
    ("Crew", "crew", "e"),
    ("Turrets", "turret_mounts", "e"),
    ("Gun Pts", "gun_ports", "e"),
    ("Spinal", "spinal_mount", "e"),
    ("Heat Cap", "heat_capacity", "e"),
    ("Heat Diss", "heat_dissipation", "e"),
    # Additional stats (scanning detail, protections, drives, misc).
    ("Cargo", "cargo_space", "e"),
    ("CargoScanEff", "cargo_scan_efficiency", "e"),
    ("CargoScanOp", "cargo_scan_opacity", "e"),
    ("OutScanEff", "outfit_scan_efficiency", "e"),
    ("OutScanOp", "outfit_scan_opacity", "e"),
    ("AtmosScan", "atmosphere_scan", "e"),
    ("AstMountJD", "asteroid_mount_jd", "e"),
    ("CoolIneff", "cooling_inefficiency", "e"),
    ("CrystalProj", "crystal_projector", "e"),
    ("DelShEn", "delayed_shield_energy", "e"),
    ("DelShGen", "delayed_shield_generation", "e"),
    ("DelShHt", "delayed_shield_heat", "e"),
    ("DepShDelay", "depleted_shield_delay", "e"),
    ("DisruptProt", "disruption_protection", "e"),
    ("Drag", "drag", "e"),
    ("Flotsam", "flotsam_chance", "e"),
    ("FuelProt", "fuel_protection", "e"),
    ("HoloEnt", "holographic_entertainment", "e"),
    ("Inertia", "inertia_reduction", "e"),
    ("JumpRange", "jump_range", "e"),
    ("Lasing", "lasing_power", "e"),
    ("MultiArmor", "multimodal_armor", "e"),
    ("Nanite", "nanite_upgrades", "e"),
    ("OptJam", "optical_jamming", "e"),
    ("PierceProt", "piercing_protection", "e"),
    ("Relay", "relay_upgrades", "e"),
    ("ShConnPt", "shield_connection_point", "e"),
    ("ShDelay", "shield_delay", "e"),
    ("ShEnX", "shield_energy_multiplier", "e"),
    ("ShFuel", "shield_fuel", "e"),
    ("ShGenX", "shield_generation_multiplier", "e"),
    ("SolarHt", "solar_heat", "e"),
    ("Hyperdrive", "hyperdrive", "e"),
    ("JumpDrive", "jump_drive", "e"),
    ("ScramDrive", "scram_drive", "e"),
    ("QuantumKey", "quantum_keystone", "e"),
]

# Hand-to-hand comparison table columns.
H2H_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Cap Atk", "capture_attack", "e"),
    ("Cap Def", "capture_defense", "e"),
]


def build_power_rows(outfits, series=None):
    """Return one row per power outfit (generators, batteries, solar, ...).

    ``series`` optionally restricts the rows to a single power series.
    """
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("series") not in POWER_SERIES:
            continue
        if series is not None and attrs.get("series") != series:
            continue
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        space = max(0.0, -number(attrs, "outfit space"))
        energy = number(attrs, "energy generation")
        heat = number(attrs, "heat generation")
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")
        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "series": attrs.get("series", ""),
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": number(attrs, "mass"),
            "space": space,
            "energy": energy,
            "energy_capacity": number(attrs, "energy capacity"),
            "heat": heat,
            "energy_per_space": energy / space if space > 0 else 0.0,
            "energy_per_heat": energy / heat if heat > 0 else 0.0,
            "solar": number(attrs, "solar collection"),
            "solar_heat": number(attrs, "solar heat"),
            "ion_resistance": number(attrs, "ion resistance"),
            "scramble_resistance": number(attrs, "scramble resistance"),
            "shield_energy_multiplier": number(attrs, "shield energy multiplier"),
            "hull_energy_multiplier": number(attrs, "hull energy multiplier"),
            "energy_consumption": number(attrs, "energy consumption"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (row["series"], -row["energy"], row["name"].lower()))
    return rows


def build_systems_rows(outfits, series=None):
    """Return one row per systems-category outfit (shields, cooling, ...).

    ``series`` optionally restricts the rows to a single system series; the
    special value "Other" matches systems that have no series attribute.
    """
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("category") != "Systems":
            continue
        actual = attrs.get("series", "")
        if series == "Other":
            if actual:
                continue
        elif series is not None and actual != series:
            continue
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        space = max(0.0, -number(attrs, "outfit space"))
        ramscoop = number(attrs, "ramscoop")
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")
        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "series": attrs.get("series", ""),
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": number(attrs, "mass"),
            "space": space,
            "shields": number(attrs, "shields"),
            "shield_generation": number(attrs, "shield generation"),
            "cooling": number(attrs, "cooling"),
            "scan_power": number(attrs, "tactical scan power"),
            "hull_repair": number(attrs, "hull repair rate"),
            "hull": number(attrs, "hull"),
            "jamming": number(attrs, "radar jamming"),
            "energy": number(attrs, "energy consumption"),
            "fuel_capacity": number(attrs, "fuel capacity"),
            "ramscoop": ramscoop,
            "ramscoop_per_space": ramscoop / space if space > 0 else 0.0,
            "ramscoop_effective": math.sqrt(max(0.0, ramscoop)),
            "ramscoop_effective_per_space": (
                math.sqrt(max(0.0, ramscoop)) / space if space > 0 else 0.0),
            "shield_energy": number(attrs, "shield energy"),
            "shield_heat": number(attrs, "shield heat"),
            "hull_energy": number(attrs, "hull energy"),
            "hull_heat": number(attrs, "hull heat"),
            "heat_generation": number(attrs, "heat generation"),
            "energy_capacity": number(attrs, "energy capacity"),
            "active_cooling": number(attrs, "active cooling"),
            "cooling_energy": number(attrs, "cooling energy"),
            "fuel_generation": number(attrs, "fuel generation"),
            "hull_repair_multiplier": number(attrs, "hull repair multiplier"),
            "cargo_scan_power": number(attrs, "cargo scan power"),
            "outfit_scan_power": number(attrs, "outfit scan power"),
            "asteroid_scan_power": number(attrs, "asteroid scan power"),
            "scan_interference": number(attrs, "scan interference"),
            "jump_speed": number(attrs, "jump speed"),
            "jump_fuel": number(attrs, "jump fuel"),
            "shield_protection": number(attrs, "shield protection"),
            "hull_protection": number(attrs, "hull protection"),
            "bunks": number(attrs, "bunks"),
            "crew": number(attrs, "required crew"),
            "turret_mounts": number(attrs, "turret mounts"),
            "gun_ports": number(attrs, "gun ports"),
            "spinal_mount": number(attrs, "spinal mount"),
            "heat_capacity": number(attrs, "heat capacity"),
            "heat_dissipation": number(attrs, "heat dissipation"),
            "cargo_space": number(attrs, "cargo space"),
            "cargo_scan_efficiency": number(attrs, "cargo scan efficiency"),
            "cargo_scan_opacity": number(attrs, "cargo scan opacity"),
            "outfit_scan_efficiency": number(attrs, "outfit scan efficiency"),
            "outfit_scan_opacity": number(attrs, "outfit scan opacity"),
            "atmosphere_scan": number(attrs, "atmosphere scan"),
            "asteroid_mount_jd": number(attrs, "asteroid mount jd"),
            "cooling_inefficiency": number(attrs, "cooling inefficiency"),
            "crystal_projector": number(attrs, "crystal projector"),
            "delayed_shield_energy": number(attrs, "delayed shield energy"),
            "delayed_shield_generation": number(attrs, "delayed shield generation"),
            "delayed_shield_heat": number(attrs, "delayed shield heat"),
            "depleted_shield_delay": number(attrs, "depleted shield delay"),
            "disruption_protection": number(attrs, "disruption protection"),
            "drag": number(attrs, "drag"),
            "flotsam_chance": number(attrs, "flotsam chance"),
            "fuel_protection": number(attrs, "fuel protection"),
            "holographic_entertainment": number(attrs, "holographic entertainment"),
            "inertia_reduction": number(attrs, "inertia reduction"),
            "jump_range": number(attrs, "jump range"),
            "lasing_power": number(attrs, "lasing power"),
            "multimodal_armor": number(attrs, "multimodal armor"),
            "nanite_upgrades": number(attrs, "nanite upgrades"),
            "optical_jamming": number(attrs, "optical jamming"),
            "piercing_protection": number(attrs, "piercing protection"),
            "relay_upgrades": number(attrs, "relay upgrades"),
            "shield_connection_point": number(attrs, "shield connection point"),
            "shield_delay": number(attrs, "shield delay"),
            "shield_energy_multiplier": number(attrs, "shield energy multiplier"),
            "shield_fuel": number(attrs, "shield fuel"),
            "shield_generation_multiplier": number(attrs, "shield generation multiplier"),
            "solar_heat": number(attrs, "solar heat"),
            "hyperdrive": number(attrs, "hyperdrive"),
            "jump_drive": number(attrs, "jump drive"),
            "scram_drive": number(attrs, "scram drive"),
            "quantum_keystone": number(attrs, "quantum keystone"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (row["series"], row["name"].lower()))
    return rows


def is_h2h(attrs):
    """An outfit is hand-to-hand if it grants capture attack or defense."""
    if attrs.get("category") == "Hand to Hand":
        return True
    if not attrs.get("category"):
        return False
    return (number(attrs, "capture attack") > 0
            or number(attrs, "capture defense") > 0)


def h2h_group(attrs):
    """The hand-to-hand sub-tab an outfit belongs to."""
    if attrs.get("series") == "Fortifications":
        return "Fortifications"
    return "H2H"


def build_h2h_rows(outfits, series=None):
    """Return one row per hand-to-hand outfit (boarding equipment).

    ``series`` optionally restricts the rows to a single hand-to-hand group.
    """
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if not is_h2h(attrs):
            continue
        group = h2h_group(attrs)
        if series is not None and group != series:
            continue
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        space = max(0.0, -number(attrs, "outfit space"))
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")
        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": number(attrs, "mass"),
            "space": space,
            "capture_attack": number(attrs, "capture attack"),
            "capture_defense": number(attrs, "capture defense"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["capture_attack"], row["name"].lower()))
    return rows


# System series handled by the Systems tab, in display order.
SYSTEM_ORDER = [
    "Shields", "Cooling", "Scanners", "Repair", "Ramscoops", "Fuel",
    "Drives", "Jammers", "Passenger", "Special Systems", "Expansions",
    "Other",
]


def series_in(outfits, predicate, order):
    """Return the ordered series present among outfits whose attrs match.

    Series with no attribute are folded into an "Other" entry.
    """
    present = set()
    for outfit in outfits:
        attrs = outfit["attrs"]
        if not predicate(attrs):
            continue
        series = attrs.get("series", "")
        present.add(series if series else "Other")
    ordered = []
    for name in order:
        if name in present:
            ordered.append(name)
    for name in sorted(present):
        if name not in ordered:
            ordered.append(name)
    return ordered


def system_series(outfits):
    """Return the ordered system series that actually contain outfits."""
    return series_in(outfits, lambda a: a.get("category") == "Systems",
                     SYSTEM_ORDER)


def engine_series(outfits):
    """Return the ordered engine series that actually contain outfits."""
    return series_in(outfits, lambda a: a.get("series") in ENGINE_SERIES,
                     ["Engines"])


def power_series(outfits):
    """Return the ordered power series that actually contain outfits."""
    return series_in(outfits, lambda a: a.get("series") in POWER_SERIES,
                     ["Generators", "Batteries", "Solar"])


def h2h_series(outfits):
    """Return the ordered hand-to-hand groups that actually contain outfits."""
    present = set()
    for outfit in outfits:
        attrs = outfit["attrs"]
        if is_h2h(attrs):
            present.add(h2h_group(attrs))
    return [group for group in ("H2H", "Fortifications") if group in present]


# Advanced engine columns: afterburners, reverse modules, and FTL drives.
ADV_ENGINE_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Type", "etype", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Aft Thr", "afterburner_thrust", "e"),
    ("Rev Thr", "reverse_thrust", "e"),
    ("Rev Thr/Space", "reverse_thrust_per_space", "e"),
    ("Jump Spd", "jump_speed", "e"),
    ("Turn", "turn", "e"),
    ("Turn/Space", "turn_per_space", "e"),
    ("En/s", "energy", "e"),
    ("Ht/s", "heat", "e"),
    ("Aft Fuel", "afterburner_fuel", "e"),
    ("Jump Fuel", "jump_fuel", "e"),
    ("Aft Shield", "afterburner_shields", "e"),
    ("Weapon Cap", "weapon_capacity", "e"),
    ("Slow Res", "slowing_resistance", "e"),
    ("Force Prot", "force_protection", "e"),
    ("Inertia", "inertia_reduction", "e"),
]

# Columns for the Unique & Special tab.
UNIQUE_COLUMNS = [
    ("Name", "name", "w"),
    ("Faction", "faction", "w"),
    ("Type", "series", "w"),
    ("Cost", "cost", "e"),
    ("Mass", "mass", "e"),
    ("Space", "space", "e"),
    ("Shields", "shields", "e"),
    ("Hull", "hull", "e"),
    ("Sh Gen", "shield_generation", "e"),
    ("Cooling", "cooling", "e"),
    ("En Gen", "energy_generation", "e"),
    ("Heat", "heat", "e"),
    ("Fuel", "fuel_capacity", "e"),
    ("Ramscp", "ramscoop", "e"),
    ("Thrust", "thrust", "e"),
    ("Turn", "turn", "e"),
    ("Bunks", "bunks", "e"),
    ("Crew", "crew", "e"),
    ("Drag", "drag", "e"),
    ("Inertia", "inertia_reduction", "e"),
    ("En Use", "energy_consumption", "e"),
    ("Flotsam", "flotsam_chance", "e"),
    ("Cloak", "cloak", "e"),
    ("Cloak En", "cloaking_energy", "e"),
    ("Cloak Fuel", "cloaking_fuel", "e"),
]

ADV_ENGINE_TYPES = ["Afterburners", "Drives", "Reverse"]


def advanced_engine_type(attrs):
    """Classify an outfit as one of the advanced engine types, or None."""
    if number(attrs, "reverse thrust") > 0:
        return "Reverse"
    if number(attrs, "afterburner thrust") > 0:
        return "Afterburners"
    for key in ("jump drive", "hyperdrive", "scram drive", "quantum keystone"):
        if number(attrs, key) > 0:
            return "Drives"
    return None


def build_advanced_engine_rows(outfits, etype=None):
    """Return one row per advanced-engine outfit (afterburner/reverse/drive)."""
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        kind = advanced_engine_type(attrs)
        if kind is None:
            continue
        if etype is not None and kind != etype:
            continue
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        space = max(0.0, -number(attrs, "outfit space"))
        reverse_thrust = number(attrs, "reverse thrust")
        turn = number(attrs, "turn")
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")
        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "etype": kind,
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": number(attrs, "mass"),
            "space": space,
            "afterburner_thrust": number(attrs, "afterburner thrust"),
            "reverse_thrust": reverse_thrust,
            "reverse_thrust_per_space": reverse_thrust / space if space > 0 else 0.0,
            "jump_speed": number(attrs, "jump speed"),
            "turn": turn,
            "turn_per_space": turn / space if space > 0 else 0.0,
            "energy": (number(attrs, "afterburner energy")
                       + number(attrs, "reverse thrusting energy")),
            "heat": (number(attrs, "afterburner heat")
                     + number(attrs, "reverse thrusting heat")),
            "afterburner_fuel": number(attrs, "afterburner fuel"),
            "jump_fuel": number(attrs, "jump fuel"),
            "afterburner_shields": number(attrs, "afterburner shields"),
            "weapon_capacity": max(0.0, number(attrs, "weapon capacity")),
            "slowing_resistance": number(attrs, "slowing resistance"),
            "force_protection": number(attrs, "force protection"),
            "inertia_reduction": number(attrs, "inertia reduction"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (row["etype"], -row["cost"], row["name"].lower()))
    return rows


def advanced_engine_types(outfits):
    """Return the ordered advanced-engine types that actually contain outfits."""
    present = set()
    for outfit in outfits:
        kind = advanced_engine_type(outfit["attrs"])
        if kind:
            present.add(kind)
    return [kind for kind in ADV_ENGINE_TYPES if kind in present]


def build_unique_rows(outfits, series=None):
    """Return one row per Unique/Special outfit."""
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("category") not in ("Unique", "Special"):
            continue
        if is_h2h(attrs):
            continue
        actual = attrs.get("series", "")
        if series == "Other":
            if actual:
                continue
        elif series is not None and actual != series:
            continue
        cost = number(attrs, "cost")
        if EXCLUDE_ZERO_COST and cost == 0:
            continue
        space = max(0.0, -number(attrs, "outfit space"))
        thumbnail = attrs.get("thumbnail", "")
        description = attrs.get("description", "")
        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "series": actual if actual else "Other",
            "description": description if isinstance(description, str) else "",
            "cost": cost,
            "mass": number(attrs, "mass"),
            "space": space,
            "shields": number(attrs, "shields"),
            "hull": number(attrs, "hull"),
            "shield_generation": number(attrs, "shield generation"),
            "cooling": number(attrs, "cooling"),
            "energy_generation": number(attrs, "energy generation"),
            "heat": number(attrs, "heat generation"),
            "fuel_capacity": number(attrs, "fuel capacity"),
            "ramscoop": number(attrs, "ramscoop"),
            "thrust": number(attrs, "thrust"),
            "turn": number(attrs, "turn"),
            "bunks": number(attrs, "bunks"),
            "crew": number(attrs, "required crew"),
            "drag": number(attrs, "drag"),
            "inertia_reduction": number(attrs, "inertia reduction"),
            "energy_consumption": number(attrs, "energy consumption"),
            "flotsam_chance": number(attrs, "flotsam chance"),
            "cloak": number(attrs, "cloak"),
            "cloaking_energy": number(attrs, "cloaking energy"),
            "cloaking_fuel": number(attrs, "cloaking fuel"),
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (row["series"], row["name"].lower()))
    return rows


def unique_series(outfits):
    """Return the ordered Unique/Special series that actually contain outfits."""
    return series_in(outfits,
                     lambda a: (a.get("category") in ("Unique", "Special")
                                and not is_h2h(a)),
                     ["Functional Unique", "Non-Functional Unique"])
