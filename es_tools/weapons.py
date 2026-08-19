"""The Weapons tab: comparison tables grouped first by mount, then by type.

The outer notebook has one tab per mount (Guns, Turrets, Secondary Weapons);
each mount tab holds an inner notebook with one tab per weapon type (beams,
projectiles, missiles, ...) that actually appears for that mount. The weapon
data is parsed once up front and shared with every table.
"""

import threading
import tkinter as tk
from tkinter import ttk

from .outfits import WEAPON_COLUMNS, build_weapon_rows, weapon_mount_types
from .parse import parse_weapon_outfits
from .paths import DATA_DIR
from .table import OutfitTableApp


class WeaponCategoryTable(OutfitTableApp):
    """Heatmap table comparing the weapons of a single weapon type."""

    COLUMNS = WEAPON_COLUMNS
    TEXT_KEYS = {"name", "faction", "mount", "type"}
    REVERSED_KEYS = {"shield_damage", "hull_damage", "disabled_damage",
                     "minable_damage", "fuel_damage", "heat_damage",
                     "energy_damage", "ion_damage", "scrambling_damage",
                     "disruption_damage", "slowing_damage", "discharge_damage",
                     "corrosion_damage", "leak_damage", "burn_damage",
                     "piercing", "hit_force", "missile_strength",
                     "blast_radius", "range", "burst_count", "dps",
                     "velocity", "lifetime", "turn", "tracking", "turret_turn"}
    RATIO_KEYS = set()
    THREE_DECIMAL_KEYS = {"energy", "heat", "reload", "dps",
                          "fuel", "burst_reload", "firing_force"}
    NOUN = "weapon"
    HAS_FACTIONS = True
    HAS_SHOW_ALL = False
    HIDE_ZERO_COLUMNS = True
    WEAPON_TYPES = None
    WEAPON_MOUNT = None
    WEAPON_OUTFITS = None

    def _load_worker(self):
        try:
            outfits = self.WEAPON_OUTFITS
            if outfits is None:
                outfits = parse_weapon_outfits(self.data_dir)
            rows = build_weapon_rows(outfits, self.WEAPON_TYPES, self.WEAPON_MOUNT)
            self.root.after(0, self._on_data_loaded, outfits, rows)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._load_error, str(exc))


class WeaponsApp(ttk.Frame):
    """Tab comparing weapons, split by mount and then by weapon type.

    Outer notebook: Guns / Turrets / Secondary Weapons.
    Inner notebook (per mount): Beams / Projectiles / Missiles / Anti-Missile /
    Tractor Beams, but only for types that actually exist in that mount.
    """

    MOUNTS = [
        ("Guns", "Guns"),
        ("Turrets", "Turrets"),
        ("Secondary Weapons", "Secondary Weapons"),
    ]

    TYPES = [
        ("Beams", ("Beam",)),
        ("Projectiles", ("Projectile",)),
        ("Missiles", ("Missile",)),
        ("Anti-Missile", ("Anti-Missile",)),
        ("Tractor Beams", ("Tractor Beam",)),
    ]

    def __init__(self, master):
        super().__init__(master)
        self.root = master.winfo_toplevel()
        self.apps = {}
        self.status_var = tk.StringVar(value="Loading weapons...")
        ttk.Label(self, textvariable=self.status_var, padding=12).pack()
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            outfits = parse_weapon_outfits(DATA_DIR)
            groups = weapon_mount_types(outfits)
            self.root.after(0, self._build_ui, outfits, groups)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._load_error, str(exc))

    def _load_error(self, message):
        self.status_var.set("Error: {}".format(message))

    def _build_ui(self, outfits, groups):
        for child in self.winfo_children():
            child.destroy()

        types_by_mount = {}
        for mount, wtype in groups:
            types_by_mount.setdefault(mount, []).append(wtype)

        outer = ttk.Notebook(self)
        outer.pack(fill=tk.BOTH, expand=True)

        for mount_label, mount in self.MOUNTS:
            present = types_by_mount.get(mount)
            if not present:
                continue

            mount_tab = ttk.Frame(outer)
            inner = ttk.Notebook(mount_tab)
            inner.pack(fill=tk.BOTH, expand=True)

            for type_label, type_tuple in self.TYPES:
                if type_tuple[0] not in present:
                    continue
                type_tab = ttk.Frame(inner)
                slug = "{}_{}".format(mount_label.lower().replace(" ", "_"),
                                      type_label.lower().replace(" ", "_"))
                cls = type("Weapons" + mount_label.replace(" ", "")
                           + type_label.replace(" ", ""),
                           (WeaponCategoryTable,),
                           {"WEAPON_TYPES": type_tuple,
                            "WEAPON_MOUNT": mount,
                            "WEAPON_OUTFITS": outfits,
                            "CONFIG_FILENAME": ".endless_sky_weapons_"
                            + slug + ".json"})
                app = cls(type_tab)
                app.pack(fill=tk.BOTH, expand=True)
                inner.add(type_tab, text=type_label)
                self.apps[slug] = app

            outer.add(mount_tab, text=mount_label)
