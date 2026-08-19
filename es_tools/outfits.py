"""Outfit data: generator, engine, and weapon row builders plus columns.

Each builder turns parsed outfits into comparable table rows. Column tuples
are (header, row key, anchor); widths are auto-sized by the table at runtime.
"""

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
        thumbnail = attrs.get("thumbnail", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
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


def build_engine_rows(outfits):
    """Return one row per engine outfit with comparable stats."""
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("series") != "Engines":
            continue

        thrust = number(attrs, "thrust")
        turn = number(attrs, "turn")
        if thrust == 0.0 and turn == 0.0:
            continue

        cost = number(attrs, "cost")
        mass = number(attrs, "mass")
        space = max(0.0, -number(attrs, "outfit space"),
                    -number(attrs, "engine capacity"))
        energy = number(attrs, "thrusting energy") + number(attrs, "turning energy")
        heat = number(attrs, "thrusting heat") + number(attrs, "turning heat")
        thumbnail = attrs.get("thumbnail", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "cost": cost,
            "mass": mass,
            "space": space,
            "thrust": thrust,
            "turn": turn,
            "energy": energy,
            "heat": heat,
            "thrust_per_space": thrust / space if space > 0 else 0.0,
            "turn_per_space": turn / space if space > 0 else 0.0,
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

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "mount": category,
            "type": wtype,
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
