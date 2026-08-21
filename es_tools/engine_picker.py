"""Engine Picker: solve the engine knapsack frontier and browse the results."""

import json
import os
import threading
import time

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton,
                               QSplitter, QStyle, QStyledItemDelegate,
                               QTableView, QVBoxLayout, QWidget)

import engine_knapsack as ek

from .config import EXCLUDE_ZERO_COST
from .images import find_plugin_images_dir
from .parse import shared_outfits
from .paths import DATA_DIR, IMAGES_DIR
from .table import _SignalBridge
from .theme import BG, FG, SELECT_BG


def pick_monospace_font():
    """Return the best available monospace font (Fira Code Nerd Font first)."""
    families = {name.lower() for name in QFontDatabase.families()}
    for name in ("Fira Code Nerd Font", "Fira Code", "Cascadia Code",
                 "Consolas", "Courier New", "DejaVu Sans Mono",
                 "Liberation Mono", "Menlo", "Monaco"):
        if name.lower() in families:
            return QFont(name)
    return QFont("monospace")


class ResultsModel(QAbstractTableModel):
    """Single-column model over the frontier results (thrust + turn)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self.max_thrust = 1.0
        self.max_turn = 1.0

    def set_results(self, results):
        self.beginResetModel()
        self.results = results
        self.max_thrust = max((r["thrust"] for r in results), default=0.0) or 1.0
        self.max_turn = max((r["turn"] for r in results), default=0.0) or 1.0
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.results)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        return None


class BarDelegate(QStyledItemDelegate):
    """Draws a row with a blue thrust bar and an orange turn bar."""

    THRUST_COLOR = QColor("#4a90d9")
    TURN_COLOR = QColor("#e08a4a")

    def paint(self, painter, option, index):
        model = index.model()
        if not isinstance(model, ResultsModel):
            super().paint(painter, option, index)
            return
        result = model.results[index.row()]

        painter.save()
        # Monospace font (set on the view) keeps the T/U labels and the
        # value decimal points aligned across rows.
        painter.setFont(option.font)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(SELECT_BG))
        else:
            painter.fillRect(option.rect, QColor(BG))

        rect = option.rect
        half = rect.height() / 2

        # Space-padded, fixed-width text: "T   450.0" / "U    12.3" so the
        # labels share a column and the decimals line up.
        thrust_text = "T {:8.1f}".format(result["thrust"])
        turn_text = "U {:8.1f}".format(result["turn"])
        metrics = painter.fontMetrics()
        text_width = max(metrics.horizontalAdvance(thrust_text),
                         metrics.horizontalAdvance(turn_text))

        # Place the bars just past the text, clamped inside the cell.
        bar_x = rect.left() + text_width + 14
        if bar_x < rect.left() + 48:
            bar_x = rect.left() + 48
        if bar_x > rect.right() - 16:
            bar_x = rect.right() - 16
        bar_width = rect.right() - bar_x - 8

        painter.setPen(QColor(FG))
        painter.drawText(
            QRect(rect.left(), rect.top(), bar_x - rect.left(), int(half)),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            thrust_text)
        if bar_width > 0:
            thrust_len = min(int(bar_width * result["thrust"] / model.max_thrust),
                             bar_width)
            painter.fillRect(bar_x, rect.top() + 4, thrust_len, 6,
                             self.THRUST_COLOR)

        painter.setPen(QColor(FG))
        painter.drawText(
            QRect(rect.left(), rect.top() + int(half), bar_x - rect.left(),
                  rect.height() - int(half)),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            turn_text)
        if bar_width > 0:
            turn_len = min(int(bar_width * result["turn"] / model.max_turn),
                           bar_width)
            painter.fillRect(bar_x, rect.top() + int(half) + 2, turn_len, 6,
                             self.TURN_COLOR)

        painter.restore()


class EnginePickerApp(QWidget):
    """Solver tab listing every non-dominated (thrust, turn) combination."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_path = os.path.join(os.path.expanduser("~"),
                                        ".endless_sky_engine_picker.json")
        self.config = self._load_config()

        self.data_dir = DATA_DIR
        self.images_dir = IMAGES_DIR
        self.plugin_images_dir = find_plugin_images_dir()
        self.outfits = None
        self.engines = []
        self.capacity = 0
        self.results = []
        self.selected = -1
        self.factions = []
        self.faction_vars = {}
        self._photo_cache = {}
        self._computing = False
        self._pending = False

        self._bridge = _SignalBridge(self)
        self._bridge.loaded.connect(self._on_loaded)
        self._bridge.failed.connect(self._compute_error)

        self._build_ui()
        self._start_loading()

    # ------------------------------------------------------------- persistence
    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return {}

    def _save_config(self):
        try:
            capacity = int(self.capacity_entry.text())
        except ValueError:
            capacity = 180
        data = {"capacity": capacity}
        if self.faction_vars:
            data["factions"] = [name for name, box in self.faction_vars.items()
                                if box.isChecked()]
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

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Engine capacity:"))
        self.capacity_entry = QLineEdit(str(self.config.get("capacity", 180)))
        self.capacity_entry.setFixedWidth(64)
        controls.addWidget(self.capacity_entry)
        self.compute_button = QPushButton("Compute")
        self.compute_button.clicked.connect(self.compute)
        self.compute_button.setEnabled(False)
        controls.addWidget(self.compute_button)
        self.status_label = QLabel("")
        controls.addWidget(self.status_label)
        controls.addStretch(1)
        root.addLayout(controls)

        self.faction_widget = QWidget()
        self.faction_layout = QGridLayout(self.faction_widget)
        self.faction_layout.setContentsMargins(0, 0, 0, 0)
        self.faction_layout.setSpacing(2)
        root.addWidget(self.faction_widget, 0,
                       Qt.AlignmentFlag.AlignLeft)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # Left: the results list with thrust/turn bars.
        self.results_view = QTableView()
        self.results_view.setFont(pick_monospace_font())
        self.results_model = ResultsModel(self)
        self.results_view.setModel(self.results_model)
        self.results_view.setItemDelegate(BarDelegate(self.results_view))
        self.results_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.results_view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_view.verticalHeader().setVisible(False)
        self.results_view.horizontalHeader().setVisible(False)
        self.results_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.results_view.verticalHeader().setDefaultSectionSize(30)
        self.results_view.setShowGrid(False)
        self.results_view.selectionModel().currentRowChanged.connect(
            self._on_result_selected)
        splitter.addWidget(self.results_view)

        # Right: summary + the selected result's engine list.
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 0, 0, 0)
        rv.setSpacing(6)
        self.summary_label = QLabel("Select a result.")
        rv.addWidget(self.summary_label, 0)
        self.engine_list = QListWidget()
        self.engine_list.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection)
        self.engine_list.setIconSize(QSize(80, 80))
        rv.addWidget(self.engine_list, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

    # ------------------------------------------------------------- loading
    def _start_loading(self):
        self._load_t0 = time.monotonic()
        self.status_label.setText("Loading outfits...")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _parsed_outfits(self):
        outfits = shared_outfits()
        if EXCLUDE_ZERO_COST:
            outfits = [outfit for outfit in outfits
                       if outfit["attrs"].get("cost", 0.0) != 0]
        return outfits

    def _load_worker(self):
        try:
            outfits = self._parsed_outfits()
            engines = ek.build_engines(outfits, [])
            factions = sorted({engine["faction"] for engine in engines})
            self._bridge.loaded.emit(("load", outfits, factions))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))

    def _build_faction_checkboxes(self, factions):
        while self.faction_layout.count():
            item = self.faction_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.factions = factions
        self.faction_vars = {}
        saved = set(self.config["factions"]) if "factions" in self.config else None
        all_checked = saved is None

        # Uniform column width based on the longest label, so the checkboxes
        # are packed to the left with even spacing instead of stretching.
        boxes = []
        for name in factions:
            box = QCheckBox(name)
            box.setChecked(all_checked or name in saved)
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
        self.compute()

    def _clear_all_factions(self):
        for box in self.faction_vars.values():
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)
        self._save_config()
        self.compute()

    def _on_faction_toggled(self, *args):
        self._save_config()
        self.compute()

    def _current_filters(self):
        if not self.factions:
            return []
        checked = [name for name, box in self.faction_vars.items()
                   if box.isChecked()]
        if not checked:
            return ["\u0000"]
        if len(checked) == len(self.factions):
            return []
        return checked

    # ------------------------------------------------------------- compute
    def compute(self):
        try:
            capacity = int(self.capacity_entry.text())
        except ValueError:
            self.status_label.setText("Capacity must be an integer.")
            return

        capacity = max(0, capacity)
        filters = self._current_filters()
        self.status_label.setText("Computing...")
        self.compute_button.setEnabled(False)
        threading.Thread(target=self._compute_worker,
                         args=(capacity, filters), daemon=True).start()

    def _compute_worker(self, capacity, filters):
        try:
            if self.outfits is None:
                self.outfits = self._parsed_outfits()
            engines = ek.prune_engines(ek.build_engines(self.outfits, filters))
            if not engines:
                self._bridge.loaded.emit(("compute", [], [], capacity))
                return
            frontier = ek.compute_frontier(capacity, engines)
            results = [{"node": node, "thrust": node.thrust,
                        "turn": node.turn, "weight": node.weight}
                       for node in frontier]
            self._bridge.loaded.emit(("compute", results, engines, capacity))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))

    def _on_loaded(self, payload):
        kind = payload[0]
        if kind == "load":
            _, outfits, factions = payload
            elapsed = (time.monotonic() - self._load_t0) * 1000.0
            print("[load] EnginePicker: {} factions in {:.0f} ms".format(
                len(factions), elapsed))
            self.outfits = outfits
            self._build_faction_checkboxes(factions)
            self.compute_button.setEnabled(True)
            self.status_label.setText("")
            self.compute()
        else:
            _, results, engines, capacity = payload
            self.results = results
            self.engines = engines
            self.capacity = capacity
            self.selected = self._balanced_index(results) if results else -1
            self.compute_button.setEnabled(True)
            if not results:
                self.status_label.setText("No matching engines found.")
                self.engine_list.clear()
                self.summary_label.setText("Select a result.")
            else:
                self.status_label.setText(
                    "{} combinations.".format(len(results)))
            self.results_model.set_results(results)
            self._select_result(self.selected)

    def _compute_error(self, message):
        self.compute_button.setEnabled(True)
        self.status_label.setText("Error: {}".format(message))

    def _balanced_index(self, results):
        if not results:
            return -1
        max_thrust = max(r["thrust"] for r in results) or 1.0
        max_turn = max(r["turn"] for r in results) or 1.0
        best = 0
        best_score = None
        for index, result in enumerate(results):
            score = abs(result["thrust"] / max_thrust
                        - result["turn"] / max_turn)
            if best_score is None or score < best_score:
                best_score = score
                best = index
        return best

    def _on_result_selected(self, current, previous):
        row = current.row()
        if 0 <= row < len(self.results):
            self.selected = row
            self._show_engines(row)

    def _select_result(self, index):
        if index < 0 or index >= len(self.results):
            return
        self.results_view.setCurrentIndex(self.results_model.index(index, 0))
        self._show_engines(index)

    def _show_engines(self, index):
        if index < 0 or index >= len(self.results):
            return
        result = self.results[index]
        counts = ek._recipe(result["node"], self.engines)

        dual, thrusters, steering = [], [], []
        for count, engine in counts.values():
            entry = (count, engine, self._thumbnail(engine))
            if engine["thrust"] > 0 and engine["turn"] > 0:
                dual.append(entry)
            elif engine["thrust"] > 0:
                thrusters.append(entry)
            else:
                steering.append(entry)
        dual.sort(key=lambda entry: (-entry[1]["thrust"], -entry[1]["turn"]))
        thrusters.sort(key=lambda entry: (-entry[1]["thrust"],
                                          -entry[1]["weight"]))
        steering.sort(key=lambda entry: (-entry[1]["turn"],
                                         -entry[1]["weight"]))

        self.engine_list.clear()
        if dual:
            self._add_header("Multi-use engines")
            for entry in dual:
                self._add_engine_item(entry)
        if thrusters:
            self._add_header("Thrusters")
            for entry in thrusters:
                self._add_engine_item(entry)
        if steering:
            self._add_header("Steering")
            for entry in steering:
                self._add_engine_item(entry)

        self.summary_label.setText(
            "Thrust {:.2f}   Turn {:.2f}   Used {}   Unused {}".format(
                result["thrust"], result["turn"],
                result["weight"], self.capacity - result["weight"]))

    def _add_header(self, text):
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.engine_list.addItem(item)

    def _add_engine_item(self, entry):
        count, engine, pixmap = entry
        text = "{}x {}  ({})\nweight {:>3}   thrust {:>7.2f}   turn {:>7.2f}".format(
            count, engine["name"], engine["faction"],
            engine["weight"], engine["thrust"], engine["turn"])
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if pixmap is not None:
            item.setIcon(pixmap)
        self.engine_list.addItem(item)

    def _thumbnail(self, engine):
        thumb = engine.get("thumbnail") or ""
        if not thumb:
            return None
        path = self._thumbnail_path(thumb)
        if not path:
            return None
        if path in self._photo_cache:
            return self._photo_cache[path]
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return None
        if "@2x" in path:
            pixmap.setDevicePixelRatio(1.0)
        # Shrink very large sprites to a sensible list icon size.
        if pixmap.width() > 160 or pixmap.height() > 160:
            pixmap = pixmap.scaled(160, 160,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        self._photo_cache[path] = pixmap
        return pixmap

    def _thumbnail_path(self, thumb):
        """Prefer the plugin's @2x sprite, falling back to the base image."""
        for images_dir in (self.plugin_images_dir, self.images_dir):
            if not images_dir:
                continue
            marker = "@2x" if images_dir == self.plugin_images_dir else ""
            path = os.path.join(images_dir, thumb + marker + ".png")
            if os.path.isfile(path):
                return path
        return None
