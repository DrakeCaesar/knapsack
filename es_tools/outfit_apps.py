"""The outfit comparison tabs built on OutfitTableApp:

* GeneratorsApp - every generator outfit
* EnginesApp    - every engine outfit
* ShipBunksApp  - every ship by maximum achievable crew capacity
"""

import os

from PySide6.QtWidgets import QApplication, QCheckBox

from .outfits import (ENGINE_COLUMNS, GENERATOR_COLUMNS,
                      build_engine_rows, build_generator_rows)
from .parse import parse_blocks
from .ships import SHIP_COLUMNS, build_rows, dedupe_rows, resolve_ships
from .table import OutfitTableApp


class GeneratorsApp(OutfitTableApp):
    """Tab that compares the stats of every generator outfit."""

    COLUMNS = GENERATOR_COLUMNS
    BUILDER = build_generator_rows
    REVERSED_KEYS = {"energy", "energy_per_space", "energy_per_heat"}
    RATIO_KEYS = {"energy_per_space", "energy_per_heat"}
    NOUN = "generator"
    CONFIG_FILENAME = ".endless_sky_generators.json"
    DEFAULT_SORT_KEY = "energy"
    DEFAULT_SORT_REVERSE = True


class EnginesApp(OutfitTableApp):
    """Tab that compares the stats of every engine outfit."""

    COLUMNS = ENGINE_COLUMNS
    BUILDER = build_engine_rows
    REVERSED_KEYS = {"thrust", "turn", "thrust_per_space", "turn_per_space"}
    RATIO_KEYS = {"thrust_per_space", "turn_per_space"}
    NOUN = "engine"
    CONFIG_FILENAME = ".endless_sky_engines.json"
    DEFAULT_SORT_KEY = "thrust"
    DEFAULT_SORT_REVERSE = True


class ShipBunksApp(OutfitTableApp):
    """Tab that lists every ship by its maximum achievable crew capacity.

    Each ship shows its game sprite beside the table. The calculation assumes
    cargo space is converted to outfit space with "Outfits Expansion" and the
    resulting outfit space is filled with "Bunk Room" outfits.
    """

    COLUMNS = SHIP_COLUMNS
    TEXT_KEYS = {"name", "display_name", "category"}
    REVERSED_KEYS = {"max_bunks", "bunks", "cargo", "outfit", "expansions",
                     "outfit_total", "bunk_rooms", "leftover_outfit",
                     "shields", "hull", "crew"}
    RATIO_KEYS = set()
    HAS_FACTIONS = False
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
