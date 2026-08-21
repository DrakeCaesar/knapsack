"""The outfit comparison tabs built on OutfitTableApp:

* EnginesApp     - every engine outfit
* PowerApp       - every power outfit (generators, batteries, solar, ...)
* HandToHandApp  - every hand-to-hand (boarding) outfit
* ShipBunksApp   - every ship by maximum achievable crew capacity
"""

import os

from PySide6.QtWidgets import (QApplication, QCheckBox, QTabWidget, QVBoxLayout,
                               QWidget)

from .outfits import (ADV_ENGINE_COLUMNS, ENGINE_COLUMNS, H2H_COLUMNS,
                      POWER_COLUMNS, UNIQUE_COLUMNS,
                      advanced_engine_types, build_advanced_engine_rows,
                      build_engine_rows, build_h2h_rows, build_power_rows,
                      build_unique_rows, h2h_series, power_series)
from .parse import parse_blocks
from .series import SeriesApp, SeriesTable
from .ships import SHIP_COLUMNS, build_rows, dedupe_rows, resolve_ships
from .table import OutfitTableApp


class EnginesTable(OutfitTableApp):
    """Tab that compares the stats of every plain engine outfit."""

    COLUMNS = ENGINE_COLUMNS
    BUILDER = build_engine_rows
    REVERSED_KEYS = {"thrust", "turn", "thrust_per_space", "turn_per_space"}
    RATIO_KEYS = {"thrust_per_space", "turn_per_space"}
    NOUN = "engine"
    CONFIG_FILENAME = ".endless_sky_engines.json"
    DEFAULT_SORT_KEY = "thrust"
    DEFAULT_SORT_REVERSE = True


class PowerTable(SeriesTable):
    """Heatmap table comparing the power outfits of a single series."""

    COLUMNS = POWER_COLUMNS
    BUILDER = build_power_rows
    TEXT_KEYS = {"name", "faction", "series"}
    REVERSED_KEYS = {"energy", "energy_capacity", "solar",
                     "energy_per_space", "energy_per_heat"}
    RATIO_KEYS = {"energy_per_space", "energy_per_heat"}
    NOUN = "power outfit"
    DEFAULT_SORT_KEY = "name"
    CONFIG_FILENAME = ".endless_sky_power.json"


class PowerApp(SeriesApp):
    """Tab comparing power outfits, split into one tab per series."""

    TABLE_CLS = PowerTable
    SERIES_FN = power_series
    LABEL = "Loading power outfits..."


class HandToHandTable(SeriesTable):
    """Heatmap table comparing the hand-to-hand outfits of a single series."""

    COLUMNS = H2H_COLUMNS
    BUILDER = build_h2h_rows
    TEXT_KEYS = {"name", "faction"}
    REVERSED_KEYS = {"capture_attack", "capture_defense"}
    RATIO_KEYS = set()
    NOUN = "hand-to-hand outfit"
    DEFAULT_SORT_KEY = "capture_attack"
    DEFAULT_SORT_REVERSE = True
    CONFIG_FILENAME = ".endless_sky_hand_to_hand.json"


class HandToHandApp(SeriesApp):
    """Tab comparing hand-to-hand outfits, split into one tab per series."""

    TABLE_CLS = HandToHandTable
    SERIES_FN = h2h_series
    LABEL = "Loading hand-to-hand outfits..."


class AdvancedEnginesTable(SeriesTable):
    """Heatmap table comparing advanced-engine outfits of one type."""

    COLUMNS = ADV_ENGINE_COLUMNS
    BUILDER = build_advanced_engine_rows
    TEXT_KEYS = {"name", "faction", "etype"}
    REVERSED_KEYS = {"afterburner_thrust", "reverse_thrust", "jump_speed"}
    RATIO_KEYS = set()
    NOUN = "advanced engine"
    DEFAULT_SORT_KEY = "name"
    CONFIG_FILENAME = ".endless_sky_advanced_engines.json"


class AdvancedEnginesApp(SeriesApp):
    """Tab comparing afterburners, reverse modules, and FTL drives."""

    TABLE_CLS = AdvancedEnginesTable
    SERIES_FN = advanced_engine_types
    LABEL = "Loading advanced engines..."


class EnginesApp(QWidget):
    """Tab comparing engines: plain engines plus advanced engine types."""

    def __init__(self, parent=None):
        super().__init__(parent)
        tabs = QTabWidget()
        tabs.addTab(EnginesTable(), "Engines")
        tabs.addTab(AdvancedEnginesApp(), "Advanced")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tabs)


class SpecialApp(OutfitTableApp):
    """Tab listing all Unique/Special outfits in one flat table."""

    COLUMNS = UNIQUE_COLUMNS
    BUILDER = build_unique_rows
    TEXT_KEYS = {"name", "faction", "series"}
    REVERSED_KEYS = set()
    RATIO_KEYS = set()
    NOUN = "special outfit"
    DEFAULT_SORT_KEY = "series"
    DEFAULT_SORT_REVERSE = False
    CONFIG_FILENAME = ".endless_sky_special.json"


class ShipBunksApp(OutfitTableApp):
    """Tab that lists every ship by its maximum achievable crew capacity.

    Each ship shows its game sprite beside the table. The calculation assumes
    cargo space is converted to outfit space with "Outfits Expansion" and the
    resulting outfit space is filled with "Bunk Room" outfits.
    """

    COLUMNS = SHIP_COLUMNS
    TEXT_KEYS = {"name", "display_name", "category", "faction"}
    REVERSED_KEYS = {"max_bunks", "bunks", "cargo", "outfit", "expansions",
                     "outfit_total", "bunk_rooms", "leftover_outfit",
                     "shields", "hull", "crew"}
    RATIO_KEYS = set()
    HAS_FACTIONS = True
    HAS_SHOW_ALL = True
    NOUN = "ship"
    CONFIG_FILENAME = ".endless_sky_ship_bunks.json"
    DEFAULT_SORT_KEY = "max_bunks"
    DEFAULT_SORT_REVERSE = True

    def _load_worker(self):
        try:
            blocks = parse_blocks(self.data_dir)
            ships = resolve_ships(blocks)
            full_rows = build_rows(ships)
            deduped = dedupe_rows(full_rows)
            self._bridge.loaded.emit((ships, full_rows, deduped))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))

    def _on_data_loaded(self, payload):
        ships, full_rows, deduped_rows = payload
        self.ships = ships
        self.full_rows = full_rows
        self.deduped_rows = deduped_rows
        if self.HAS_FACTIONS:
            self._build_faction_checkboxes(
                sorted({row["faction"] for row in full_rows}))
        self._refresh_rows()

    def _base_rows(self):
        if self.show_all_var is None:
            return self.deduped_rows
        return self.full_rows if self.show_all_var.isChecked() else self.deduped_rows

    def _build_extra_bar(self, layout):
        self.show_all_var = QCheckBox("Show all variants")
        self.show_all_var.setChecked(bool(self.config.get("show_all", False)))
        self.show_all_var.toggled.connect(self._on_show_all)
        layout.addWidget(self.show_all_var)

    def _on_show_all(self, *args):
        if not self.full_rows:
            return
        self._save_config()
        self._refresh_rows()

    def _row_image_path(self, row):
        """Return the on-disk path to the ship sprite, or its first frame."""
        key = (row.get("sprite", ""), row.get("thumbnail", ""))
        if key in self._path_cache:
            return self._path_cache[key]
        path = self._resolve_ship_image(row)
        self._path_cache[key] = path
        return path

    def _resolve_ship_image(self, row):
        sprite = row.get("sprite", "")
        if sprite:
            for images_dir in self._image_dirs():
                marker = "@2x" if images_dir == self.plugin_images_dir else ""
                path = os.path.join(images_dir, sprite + marker + ".png")
                if os.path.isfile(path):
                    return path
                frame = self._first_frame(images_dir, sprite, marker)
                if frame:
                    return frame
        thumbnail = row.get("thumbnail", "")
        if thumbnail:
            for images_dir in self._image_dirs():
                marker = "@2x" if images_dir == self.plugin_images_dir else ""
                path = os.path.join(images_dir, thumbnail + marker + ".png")
                if os.path.isfile(path):
                    return path
        return None

    def _preview_title(self, row):
        return row["display_name"]

    def _extra_preview_lines(self, row):
        if row["display_name"] != row["name"]:
            return ["Source name: {}".format(row["name"])]
        return []

    def _build_context_menu(self, menu):
        menu.addAction("Copy Source Name", lambda: self._copy_field("name"))
        menu.addAction("Copy In-Game Name",
                       lambda: self._copy_field("display_name"))
        menu.addSeparator()
        menu.addAction("Copy Both Names", self._copy_both_names)

    def _copy_field(self, key):
        index = self.view.currentIndex()
        if self.rows and index.isValid():
            QApplication.clipboard().setText(str(self.rows[index.row()][key]))

    def _copy_both_names(self):
        index = self.view.currentIndex()
        if self.rows and index.isValid():
            row = self.rows[index.row()]
            QApplication.clipboard().setText(
                "{}\t{}".format(row["name"], row["display_name"]))

    def _image_dirs(self):
        """Yield the image roots to search, plugin first when present."""
        if self.plugin_images_dir:
            yield self.plugin_images_dir
        yield self.images_dir

    def _first_frame(self, images_dir, sprite, marker):
        """Find the lowest-numbered animation frame for a sprite path."""
        parent = os.path.dirname(sprite)
        base = os.path.basename(sprite)
        if not parent or not base:
            return None

        directory = os.path.join(images_dir, parent)
        if not os.path.isdir(directory):
            return None

        prefix = base + "-"
        suffix = marker + ".png"
        candidates = []
        for name in os.listdir(directory):
            if name.startswith(prefix) and name.endswith(suffix):
                middle = name[len(prefix):-len(suffix)]
                if middle.isdigit():
                    candidates.append((int(middle), name))

        if not candidates:
            return None
        candidates.sort()
        return os.path.join(directory, candidates[0][1])
