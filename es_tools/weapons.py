"""The Weapons tab: weapon comparison tables grouped by weapon type."""

import tkinter as tk
from tkinter import ttk

from .outfits import WEAPON_COLUMNS, build_weapon_rows
from .parse import parse_weapon_outfits
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
    WEAPON_TYPES = None

    def _load_worker(self):
        try:
            outfits = parse_weapon_outfits(self.data_dir)
            rows = build_weapon_rows(outfits, self.WEAPON_TYPES)
            self.root.after(0, self._on_data_loaded, outfits, rows)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._load_error, str(exc))


class WeaponsApp(ttk.Frame):
    """Tab with a sub-tab per weapon type, comparing all of their stats.

    Weapons are grouped by how they behave (beams, projectiles, missiles, ...)
    instead of by mount, so weapons that share a group of statistics are
    compared together. The "Mount" column still shows whether each weapon is a
    gun, turret, or secondary weapon.
    """

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
        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        for label, types in self.TYPES:
            tab = ttk.Frame(notebook)
            slug = label.lower().replace(" ", "_")
            cls = type("Weapons" + label.replace(" ", ""),
                       (WeaponCategoryTable,),
                       {"WEAPON_TYPES": types,
                        "CONFIG_FILENAME": ".endless_sky_weapons_" + slug + ".json"})
            app = cls(tab)
            app.pack(fill=tk.BOTH, expand=True)
            notebook.add(tab, text=label)
            self.apps[label] = app
