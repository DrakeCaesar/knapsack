"""The Weapons tab: comparison tables grouped first by mount, then by type.

The outer tab widget has one tab per mount (Guns, Turrets, Secondary Weapons);
each mount tab holds an inner tab widget with one tab per weapon type that
actually appears for that mount. The weapon data is parsed once up front and
shared with every table.
"""

import threading
import time

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from .outfits import WEAPON_COLUMNS, build_weapon_rows, weapon_mount_types
from .parse import shared_weapons
from .table import OutfitTableApp, _SignalBridge


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
                outfits = shared_weapons()
            rows = build_weapon_rows(outfits, self.WEAPON_TYPES, self.WEAPON_MOUNT)
            self._bridge.loaded.emit((outfits, rows))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))


class WeaponsApp(QWidget):
    """Tab comparing weapons, split by mount and then by weapon type."""

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.apps = {}
        self._load_t0 = time.monotonic()
        self._bridge = _SignalBridge(self)
        self._bridge.loaded.connect(self._build_ui)
        self._bridge.failed.connect(self._load_error)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("Loading weapons...")
        layout.addWidget(self.status_label, 0)

        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            outfits = shared_weapons()
            groups = weapon_mount_types(outfits)
            self._bridge.loaded.emit((outfits, groups))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))

    def _load_error(self, message):
        self.status_label.setText("Error: {}".format(message))

    def _build_ui(self, payload):
        outfits, groups = payload
        elapsed = (time.monotonic() - self._load_t0) * 1000.0
        print("[load] WeaponsApp: {} groups in {:.0f} ms".format(
            len(groups), elapsed))
        self.status_label.hide()

        types_by_mount = {}
        for mount, wtype in groups:
            types_by_mount.setdefault(mount, []).append(wtype)

        outer = QTabWidget()
        self.layout().addWidget(outer, 1)

        for mount_label, mount in self.MOUNTS:
            present = types_by_mount.get(mount)
            if not present:
                continue

            inner = QTabWidget()
            for type_label, type_tuple in self.TYPES:
                if type_tuple[0] not in present:
                    continue
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
                inner.addTab(cls(), type_label)
                self.apps[slug] = inner.widget(inner.count() - 1)

            outer.addTab(inner, mount_label)
