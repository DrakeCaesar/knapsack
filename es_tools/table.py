"""Qt heatmap table widget for comparing outfit stats.

Replaces the old tkinter canvas table with a QTableView + model + delegate,
so Qt only paints the visible cells and provides native scrolling, sorting,
and selection. The row data and column definitions are still provided by the
pure-Python data modules.
"""

import json
import math
import os
import threading
import time

from PySide6.QtCore import (QAbstractTableModel, QModelIndex, QObject, QTimer,
                            Qt, Signal)
from PySide6.QtGui import QColor, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                               QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QMenu, QPushButton, QScrollArea, QSplitter,
                               QStyle, QStyledItemDelegate, QTableView,
                               QVBoxLayout, QWidget)

import engine_knapsack as ek

from .config import PRELOAD_IMAGES
from .images import find_plugin_images_dir
from .parse import shared_outfits
from .paths import DATA_DIR, IMAGES_DIR
from .theme import BG, ENTRY_BG, FG, SELECT_BG

# Custom role used by the delegate to fetch the raw (unformatted) cell value.
RAW_ROLE = int(Qt.ItemDataRole.UserRole) + 1

# Color of the vertical separators drawn between column groups.
SECTION_BORDER = "#000000"


def heat_color(t):
    """Interpolate a dark green -> orange -> red heatmap color."""
    stops = ((24, 90, 33), (190, 100, 0), (170, 25, 25))
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        u = t * 2.0
        a, b = stops[0], stops[1]
    else:
        u = (t - 0.5) * 2.0
        a, b = stops[1], stops[2]
    return QColor(int(round(a[0] + (b[0] - a[0]) * u)),
                  int(round(a[1] + (b[1] - a[1]) * u)),
                  int(round(a[2] + (b[2] - a[2]) * u)))


def cell_color(value, min_v, max_v, reverse=False):
    """Map a value within [min_v, max_v] to its heatmap color.

    Uses a log1p scale so a few extreme outliers (e.g. one 1B ship among
    10M ships) don't squash the rest of the column into a single color.
    """
    lo = math.log1p(max(min_v, 0.0))
    hi = math.log1p(max(max_v, 0.0))
    v = math.log1p(max(value, 0.0))
    span = hi - lo
    t = 0.5 if span == 0 else (v - lo) / span
    if reverse:
        t = 1.0 - t
    return heat_color(t)


def png_width(path):
    """Read a PNG file's pixel width from its header without full decoding."""
    with open(path, "rb") as handle:
        data = handle.read(24)
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return 0
    return int.from_bytes(data[16:20], "big")


class _SignalBridge(QObject):
    """Thread-safe bridge: worker threads emit these to reach the UI thread."""

    loaded = Signal(object)
    failed = Signal(str)
    measured = Signal(int, float)


class OutfitTableModel(QAbstractTableModel):
    """Tabular model over a list of row dicts plus visible column defs."""

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.rows = []
        self.columns = []
        self.scales = {}
        self.decimals = {}

    def set_rows(self, rows):
        """Replace all rows and refresh column/scaling metadata."""
        self.beginResetModel()
        self.rows = rows
        self._sync_meta()
        self.endResetModel()

    def _sync_meta(self):
        self.columns = list(self.table._visible_columns())
        self.scales = dict(self.table._scales)
        self.decimals = dict(self.table._decimals)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        _, key, _ = self.columns[index.column()]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            value = row[key]
            # Zero cells render blank (and uncolored) so they read as "none".
            if isinstance(value, (int, float)) and value == 0:
                return ""
            return self.table._format_cell(row, key, self.decimals.get(key, 0))
        if role == RAW_ROLE:
            return row[key]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            anchor = self.columns[index.column()][2]
            if anchor == "e":
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (orientation == Qt.Orientation.Horizontal
                and role == Qt.ItemDataRole.DisplayRole
                and 0 <= section < len(self.columns)):
            return self.columns[section][0]
        return None

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if column < 0 or column >= len(self.columns):
            return
        self.table._sort_key = self.columns[column][1]
        self.table._sort_reverse = (order == Qt.SortOrder.DescendingOrder)

        # Remember which item is selected so we can keep it selected after
        # the rows are reordered (instead of keeping the same row index,
        # which would now hold a different item).
        view = self.table.view
        selected_row = None
        index = view.currentIndex()
        if index.isValid() and 0 <= index.row() < len(self.rows):
            selected_row = self.rows[index.row()]

        self.layoutAboutToBeChanged.emit()
        # Mutate in place so self.rows (the model) and self.table.rows stay
        # the same list; otherwise the preview would read stale positions.
        self.rows[:] = self.table._sorted_rows(self.rows)
        self.layoutChanged.emit()

        if selected_row is not None:
            for row, candidate in enumerate(self.rows):
                if candidate is selected_row:
                    view.setCurrentIndex(self.index(row, 0))
                    break
        # Always return to the top of the list after a sort, rather than
        # scrolling to wherever the selected item landed.
        view.scrollToTop()


class HeatmapDelegate(QStyledItemDelegate):
    """Paints each cell with its heatmap color and the formatted text."""

    def paint(self, painter, option, index):
        model = index.model()
        if not isinstance(model, OutfitTableModel):
            super().paint(painter, option, index)
            return

        key = model.columns[index.column()][1]
        value = model.data(index, RAW_ROLE)
        scales = model.scales

        painter.save()

        if key in scales and isinstance(value, (int, float)) and value != 0:
            color = cell_color(value, *scales[key],
                               reverse=(key in model.table.reversed_keys))
        else:
            # Zero-valued cells (and any non-numeric cells) get no heat tint,
            # so they read as "none" rather than as the lowest/highest value.
            color = QColor(ENTRY_BG)
        painter.fillRect(option.rect, color)

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected:
            overlay = QColor(SELECT_BG)
            overlay.setAlpha(150)
            painter.fillRect(option.rect, overlay)

        text = model.data(index, Qt.ItemDataRole.DisplayRole) or ""
        align = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        painter.setPen(QColor("#ffffff") if selected else QColor(FG))
        painter.drawText(option.rect.adjusted(6, 0, -6, 0),
                         Qt.AlignmentFlag(align), text)

        # Vertical separator at the start of a new column group, drawn on top
        # of the cell fill so it stays visible over the heatmap colors.
        if key in getattr(model.table, "SECTION_KEYS", ()):
            painter.setPen(QPen(QColor(SECTION_BORDER), 1))
            x = option.rect.left()
            painter.drawLine(x, option.rect.top(), x, option.rect.bottom())
        painter.restore()


class OutfitTableApp(QWidget):
    """Reusable heatmap table for comparing outfit stats."""

    COLUMNS = []
    # Column keys that start a new group; a vertical separator is drawn before
    # them in the heatmap delegate.
    SECTION_KEYS = set()
    BUILDER = None
    REVERSED_KEYS = set()
    RATIO_KEYS = set()
    THREE_DECIMAL_KEYS = {"energy", "heat", "reload", "dps"}
    NOUN = "outfit"
    CONFIG_FILENAME = ".endless_sky_outfits.json"
    DEFAULT_SORT_KEY = "name"
    DEFAULT_SORT_REVERSE = False
    TEXT_KEYS = {"name", "faction"}
    HAS_FACTIONS = True
    HAS_SHOW_ALL = False
    # When True, numeric columns that are all zero for every row are hidden.
    HIDE_ZERO_COLUMNS = False

    ROW_H = 24
    # Extra total horizontal padding added when auto-sizing column widths; it
    # is split evenly on either side of the widest cell text.
    CELL_PADDING = 16
    # Minimum width kept for the right-hand preview panel when the splitter is
    # auto-adjusted to make room for the full table.
    MIN_PREVIEW_WIDTH = 480

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort_key = self.DEFAULT_SORT_KEY
        self._sort_reverse = self.DEFAULT_SORT_REVERSE

        self.config_path = os.path.join(os.path.expanduser("~"),
                                        self.CONFIG_FILENAME)
        self.config = self._load_config()

        self.data_dir = DATA_DIR
        self.images_dir = IMAGES_DIR
        self.plugin_images_dir = find_plugin_images_dir()

        self.outfits = []
        self.all_rows = []
        self.full_rows = []
        self.deduped_rows = []
        self.rows = []
        self.factions = []
        self.faction_vars = {}
        self._pixmap_cache = {}
        self._path_cache = {}
        self.show_all_var = None
        self.numeric_keys = [key for _, key, _ in self.COLUMNS
                             if key not in self.TEXT_KEYS]
        self.reversed_keys = self.REVERSED_KEYS
        self._scales = {}
        self._decimals = {}
        self._preload_timer = None
        self._preload_paths = []
        self._preload_index = 0
        self._table_desired_width = 0
        self._splitter_fit = False
        self._measure_generation = 0
        self._load_t0 = 0.0
        self._measure_t0 = 0.0
        self._measure_count = 0

        self._bridge = _SignalBridge(self)
        self._bridge.loaded.connect(self._on_data_loaded)
        self._bridge.failed.connect(self._load_error)
        self._bridge.measured.connect(self._on_measured)

        self._build_ui()
        self._start_loading()

    # ------------------------------------------------------------ persistence
    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return {}

    def _save_config(self):
        data = {}
        if self.HAS_FACTIONS and self.faction_vars:
            data["factions"] = [name for name, cb in self.faction_vars.items()
                                if cb.isChecked()]
        if self.HAS_SHOW_ALL and self.show_all_var is not None:
            data["show_all"] = bool(self.show_all_var.isChecked())
        try:
            with open(self.config_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError:
            pass

    # -------------------------------------------------------------------- UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        top = QHBoxLayout()
        self.status_label = QLabel("")
        top.addWidget(self.status_label)
        top.addStretch(1)
        self._build_extra_bar(top)
        root.addLayout(top)

        if self.HAS_FACTIONS:
            self.faction_widget = QWidget()
            self.faction_layout = QGridLayout(self.faction_widget)
            self.faction_layout.setContentsMargins(0, 0, 0, 0)
            self.faction_layout.setSpacing(2)
            root.addWidget(self.faction_widget, 0,
                           Qt.AlignmentFlag.AlignLeft)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(self.splitter, 1)

        # Left: the heatmap table.
        self.view = QTableView()
        self.model = OutfitTableModel(self)
        self.view.setModel(self.model)
        self.view.setItemDelegate(HeatmapDelegate(self.view))
        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setShowGrid(False)
        self.view.verticalHeader().setVisible(False)
        self.view.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._on_context_menu)
        self.view.selectionModel().currentRowChanged.connect(
            self._on_current_row_changed)
        self.splitter.addWidget(self.view)

        # Right: thumbnail + stats preview.
        self.preview = QWidget()
        pv = QVBoxLayout(self.preview)
        pv.setContentsMargins(6, 6, 6, 6)
        pv.setSpacing(6)
        self.name_label = QLabel("")
        font = self.name_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self.name_label.setFont(font)
        pv.addWidget(self.name_label)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        self.thumb_label = QLabel("")
        self.thumb_label.setStyleSheet("border: 1px solid #777777;")
        self.scroll_area.setWidget(self.thumb_label)
        pv.addWidget(self.scroll_area, 1)
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignTop
                                            | Qt.AlignmentFlag.AlignLeft)
        self.description_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.description_label.setStyleSheet("color: #b0b0b0;")
        pv.addWidget(self.description_label)
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignTop
                                      | Qt.AlignmentFlag.AlignLeft)
        self.stats_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        pv.addWidget(self.stats_label)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

    def _start_loading(self):
        self._load_t0 = time.monotonic()
        self.status_label.setText("Loading {}s...".format(self.NOUN))
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            outfits = shared_outfits()
            rows = type(self).BUILDER(outfits)
            self._bridge.loaded.emit((outfits, rows))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))

    def _on_data_loaded(self, payload):
        outfits, rows = payload
        elapsed = (time.monotonic() - self._load_t0) * 1000.0
        print("[load] {}: {} rows in {:.0f} ms".format(
            self.NOUN, len(rows), elapsed))
        self.outfits = outfits
        self.all_rows = rows
        if self.HAS_FACTIONS:
            self._build_faction_checkboxes(sorted({row["faction"] for row in rows}))
        self._refresh_rows()

    def _load_error(self, message):
        self.status_label.setText("Error: {}".format(message))

    # ----------------------------------------------------------- faction bar
    def _build_faction_checkboxes(self, factions):
        while self.faction_layout.count():
            item = self.faction_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.factions = factions
        self.faction_vars = {}
        saved = set(self.config["factions"]) if "factions" in self.config else None

        # Uniform column width based on the longest label, so the checkboxes
        # are packed to the left with even spacing instead of stretching.
        boxes = []
        for name in factions:
            box = QCheckBox(name)
            box.setChecked(saved is None or name in saved)
            box.toggled.connect(self._on_faction_toggled)
            self.faction_vars[name] = box
            boxes.append(box)

        width = max((box.sizeHint().width() for box in boxes), default=0)
        columns = 6
        # "Select all" / "Clear all" stacked to the left of the checkboxes.
        self.select_all_button = QPushButton("Select all")
        self.clear_all_button = QPushButton("Clear all")
        self.select_all_button.clicked.connect(self._select_all_factions)
        self.clear_all_button.clicked.connect(self._clear_all_factions)
        # Match the buttons' height to the checkboxes so the grid rows (and
        # the gaps between checkbox rows) stay uniform.
        box_height = max((box.sizeHint().height() for box in boxes), default=20)
        for button in (self.select_all_button, self.clear_all_button):
            button.setFixedHeight(box_height)
            button.setStyleSheet(
                "QPushButton { background: #333333; border: 1px solid #444444;"
                " padding: 0 10px; }"
                "QPushButton:hover { background: #3c3c3c; }")
        self.faction_layout.addWidget(self.select_all_button, 0, 0)
        self.faction_layout.addWidget(self.clear_all_button, 1, 0)
        for index, box in enumerate(boxes):
            box.setMinimumWidth(width)
            self.faction_layout.addWidget(box, index // columns,
                                          1 + index % columns)

    def _select_all_factions(self):
        for box in self.faction_vars.values():
            box.blockSignals(True)
            box.setChecked(True)
            box.blockSignals(False)
        self._save_config()
        self._refresh_rows()

    def _clear_all_factions(self):
        for box in self.faction_vars.values():
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)
        self._save_config()
        self._refresh_rows()

    def _on_faction_toggled(self, *args):
        self._save_config()
        self._refresh_rows()

    def _current_factions(self):
        if not self.factions:
            return None
        checked = {name for name, box in self.faction_vars.items()
                   if box.isChecked()}
        if not checked:
            return set()
        if len(checked) == len(self.factions):
            return None
        return checked

    # -------------------------------------------------------------- refresh
    def _refresh_rows(self):
        base = self._base_rows()
        filters = self._current_factions()
        if filters is None:
            self.rows = list(base)
        else:
            self.rows = [row for row in base if row["faction"] in filters]
        self.rows = self._sorted_rows(self.rows)
        self._recompute_columns()
        self.model.set_rows(self.rows)
        self._measure_widest_sprite_async()
        self._auto_size_columns()
        self._select_first()
        self._start_preload()

    def _start_preload(self):
        """Eagerly load every thumbnail when PRELOAD_IMAGES is enabled."""
        if self._preload_timer is not None:
            self._preload_timer.stop()
            self._preload_timer = None

        if not PRELOAD_IMAGES:
            self._update_preload_status()
            return

        paths = []
        seen = set()
        for row in self.rows:
            path = self._row_image_path(row)
            if path and path not in seen:
                seen.add(path)
                paths.append(path)

        self._preload_paths = paths
        self._preload_index = 0
        self._update_preload_status()

        if paths:
            self._preload_timer = QTimer(self)
            self._preload_timer.setInterval(0)
            self._preload_timer.timeout.connect(self._preload_tick)
            self._preload_timer.start()

    def _preload_tick(self):
        """Load a small batch of thumbnails, then yield to the event loop."""
        start = time.monotonic()
        while self._preload_index < len(self._preload_paths):
            path = self._preload_paths[self._preload_index]
            self._preload_index += 1
            if path not in self._pixmap_cache:
                self._load_pixmap(path)
            if time.monotonic() - start > 0.012:
                break
        self._update_preload_status()
        if self._preload_index >= len(self._preload_paths):
            self._preload_timer.stop()
            self._preload_timer = None

    def _update_preload_status(self):
        total = len(self.rows)
        if total == 0:
            self.status_label.setText("No {}s.".format(self.NOUN))
            return
        if not PRELOAD_IMAGES:
            self.status_label.setText("{} {}s".format(total, self.NOUN))
            return
        loaded = 0
        for row in self.rows:
            path = self._row_image_path(row)
            if path is None or path in self._pixmap_cache:
                loaded += 1
        if loaded >= total:
            self.status_label.setText("{} {}s".format(total, self.NOUN))
        else:
            self.status_label.setText(
                "{} / {} {}s loaded".format(loaded, total, self.NOUN))

    def _sorted_rows(self, rows):
        key = self._sort_key
        reverse = self._sort_reverse

        def sort_value(row):
            value = row.get(key, "")
            return value.lower() if isinstance(value, str) else value

        return sorted(rows, key=sort_value, reverse=reverse)

    def _select_first(self):
        if self.rows:
            self.view.setCurrentIndex(self.model.index(0, 0))
        else:
            self.name_label.setText("")
            self.stats_label.setText("")
            self.description_label.setText("")
            self.description_label.hide()
            self.thumb_label.clear()

    def _on_current_row_changed(self, current, previous):
        row = current.row()
        rows = self.model.rows
        if 0 <= row < len(rows):
            self._show_preview(rows[row])

    # ------------------------------------------------------------- columns
    def _header_for(self, key):
        for header, k, _ in self.COLUMNS:
            if k == key:
                return header
        return key

    def _decimal_places(self, value):
        if not isinstance(value, float):
            return 0
        if value == int(value):
            return 0
        text = repr(value)
        if "." not in text:
            return 0
        return len(text.split(".", 1)[1].rstrip("0"))

    def _format_cell(self, row, key, decimals):
        value = row[key]
        if isinstance(value, str):
            return value
        return format(value, ",.{0}f".format(decimals))

    def _recompute_columns(self):
        self._decimals = {}
        self._scales = {}
        for key in self.numeric_keys:
            values = [row[key] for row in self.rows]
            if not values:
                continue
            if key in self.RATIO_KEYS or key in self.THREE_DECIMAL_KEYS:
                self._decimals[key] = 3
            else:
                self._decimals[key] = max(self._decimal_places(value)
                                          for value in values)
            self._scales[key] = (min(values), max(values))

    def _visible_columns(self):
        if not self.HIDE_ZERO_COLUMNS:
            return self.COLUMNS
        hidden = set()
        for key in self.numeric_keys:
            values = [row[key] for row in self.rows]
            if values and all(value == 0 for value in values):
                hidden.add(key)
        return [column for column in self.COLUMNS if column[1] not in hidden]

    def _auto_size_columns(self):
        metrics = self.view.fontMetrics()
        header = self.view.horizontalHeader()
        total = 0
        for column, (column_header, key, _anchor) in enumerate(self.model.columns):
            longest = metrics.horizontalAdvance(column_header)
            for row in self.rows:
                text = self._format_cell(row, key, self._decimals.get(key, 0))
                longest = max(longest, metrics.horizontalAdvance(text))
            self.view.setColumnWidth(column, longest + self.CELL_PADDING)
            total += longest + self.CELL_PADDING
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Include room for the vertical scrollbar so columns aren't pushed
        # behind it, then make the splitter give the table that much room.
        total += self.view.verticalScrollBar().sizeHint().width()
        self._table_desired_width = total
        self._splitter_fit = False
        self._fit_splitter()

    def _measure_widest_sprite_async(self):
        """Find the widest sprite in this list without blocking the UI.

        PNG dimensions live in the first 24 bytes, so this is a tiny read per
        file. The scan runs on a worker thread and reports back through the
        signal bridge so the main thread stays responsive.
        """
        paths = []
        seen = set()
        for row in self.rows:
            path = self._row_image_path(row)
            if path and path not in seen:
                seen.add(path)
                paths.append(path)

        self._measure_generation += 1
        generation = self._measure_generation
        self._measure_t0 = time.monotonic()
        self._measure_count = len(paths)
        if not paths:
            self._apply_measured_width(0)
            return

        def run():
            widest = 0.0
            for path in paths:
                try:
                    width = png_width(path)
                except OSError:
                    width = 0
                if width > widest:
                    widest = width
            self._bridge.measured.emit(generation, float(widest))

        threading.Thread(target=run, daemon=True).start()

    def _on_measured(self, generation, widest):
        if generation != self._measure_generation:
            return  # stale result from an earlier list
        elapsed = (time.monotonic() - self._measure_t0) * 1000.0
        print("[sprites] {}: {} files in {:.0f} ms".format(
            self.NOUN, self._measure_count, elapsed))
        self._apply_measured_width(widest)

    def _apply_measured_width(self, widest):
        max_width = int(widest) + 24 if widest else self.MIN_PREVIEW_WIDTH
        self.preview.setMaximumWidth(max(max_width, self.MIN_PREVIEW_WIDTH))
        self._splitter_fit = False
        self._fit_splitter()

    def _fit_splitter(self):
        """Size the table and the right-hand preview panel.

        Prefers to show every table column alongside a preview panel wide
        enough for the widest sprite. If the table is wider than the window,
        the preview still gets as much room as it can and the table scrolls
        horizontally. Only does this once per data refresh (and once when the
        tab is first shown) so it never fights the user's own splitter drags.
        """
        if self._splitter_fit:
            return
        available = self.splitter.width()
        if available <= 0 or self._table_desired_width <= 0:
            return
        table_width = self._table_desired_width
        preview_needed = max(self.preview.maximumWidth(), self.MIN_PREVIEW_WIDTH)

        if available >= table_width + preview_needed + 10:
            # Everything fits: table shows all columns, preview gets the rest.
            self.splitter.setSizes([table_width, available - table_width])
        else:
            # Table too wide for the window: size the preview to the widest
            # sprite (capped so the table stays usable) and let the table
            # scroll horizontally.
            preview_size = min(preview_needed, int(available * 0.6))
            table_size = max(1, available - preview_size)
            self.splitter.setSizes([table_size, preview_size])
        self._splitter_fit = True

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_splitter()

    # -------------------------------------------------------------- preview
    def _show_preview(self, row):
        self.name_label.setText(self._preview_title(row))

        path = self._row_image_path(row)
        if path:
            pixmap = self._load_pixmap(path)
            self.thumb_label.setPixmap(pixmap if pixmap is not None
                                       else QPixmap())
        else:
            self.thumb_label.clear()
        # Resize the label to the pixmap's size hint; otherwise the scroll area
        # keeps it at its previous (tiny) size and crops the image.
        self.thumb_label.adjustSize()

        decimals = self._decimals
        lines = list(self._extra_preview_lines(row))
        for header, key, _ in self._visible_columns():
            if key == "name":
                continue
            value = row.get(key, "")
            if isinstance(value, str):
                lines.append("{}: {}".format(header, value))
            else:
                lines.append("{}: {}".format(
                    header, self._format_cell(row, key, decimals.get(key, 0))))
        self.stats_label.setText("\n".join(lines))

        description = row.get("description", "")
        if isinstance(description, str) and description:
            self.description_label.setText(description)
            self.description_label.show()
        else:
            self.description_label.setText("")
            self.description_label.hide()

    def _load_pixmap(self, path):
        """Load a sprite at its full pixel resolution.

        @2x sprites are shown at their native (2x) size rather than downscaled,
        so Qt's automatic @2x device-pixel-ratio detection is overridden.
        """
        if path in self._pixmap_cache:
            return self._pixmap_cache[path]
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        if "@2x" in path:
            pixmap.setDevicePixelRatio(1.0)
        self._pixmap_cache[path] = pixmap
        return pixmap

    def _outfit_image_path(self, row):
        thumbnail = row.get("thumbnail", "")
        if not thumbnail:
            return None
        for images_dir in (self.plugin_images_dir, self.images_dir):
            if not images_dir:
                continue
            marker = "@2x" if images_dir == self.plugin_images_dir else ""
            path = os.path.join(images_dir, thumbnail + marker + ".png")
            if os.path.isfile(path):
                return path
        return None

    def _row_image_path(self, row):
        """Return the image path for a row; subclasses may override."""
        return self._outfit_image_path(row)

    # --------------------------------------------------------------- hooks
    def _base_rows(self):
        return self.all_rows

    def _build_extra_bar(self, layout):
        """Hook for subclasses to add extra top-bar controls."""

    def _build_context_menu(self, menu):
        menu.addAction("Copy Name", self._copy_name)

    def _preview_title(self, row):
        return row["name"]

    def _extra_preview_lines(self, row):
        return []

    def _on_context_menu(self, pos):
        index = self.view.indexAt(pos)
        if not index.isValid():
            return
        self.view.setCurrentIndex(self.model.index(index.row(), 0))
        menu = QMenu(self)
        self._build_context_menu(menu)
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def _copy_name(self):
        index = self.view.currentIndex()
        rows = self.model.rows
        if rows and index.isValid():
            QApplication.clipboard().setText(
                str(rows[index.row()]["name"]))
