"""Generic 'split by type/series' wrapper for outfit comparison tabs.

Each series (e.g. "Engines", "Afterburners", "Drives") gets its own sub-tab
inside a SeriesApp, so the stats are comparable within each group. The outfit
data is parsed once and shared with every table.
"""

import threading

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

import engine_knapsack as ek

from .paths import DATA_DIR
from .table import OutfitTableApp, _SignalBridge


class SeriesTable(OutfitTableApp):
    """Heatmap table comparing outfits of a single series/type."""

    COLUMNS = []
    BUILDER = None
    TEXT_KEYS = {"name", "faction", "series"}
    REVERSED_KEYS = set()
    RATIO_KEYS = set()
    NOUN = "outfit"
    HAS_FACTIONS = True
    HIDE_ZERO_COLUMNS = True
    DEFAULT_SORT_KEY = "name"
    DEFAULT_SORT_REVERSE = False
    CONFIG_FILENAME = ".endless_sky_outfits.json"
    SERIES = None
    SERIES_OUTFITS = None

    def _load_worker(self):
        try:
            outfits = self.SERIES_OUTFITS
            if outfits is None:
                outfits = ek.parse_outfits(self.data_dir)
            # Access BUILDER via the class, not the instance, so it is not
            # bound (otherwise "self" is prepended as an extra argument).
            rows = type(self).BUILDER(outfits, self.SERIES)
            self._bridge.loaded.emit((outfits, rows))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))


class SeriesApp(QWidget):
    """Outfit comparison tab split into one sub-tab per series/type."""

    TABLE_CLS = None
    SERIES_FN = None
    LABEL = "Loading..."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.apps = {}
        self._bridge = _SignalBridge(self)
        self._bridge.loaded.connect(self._build_ui)
        self._bridge.failed.connect(self._load_error)

        layout = QVBoxLayout(self)
        self.status_label = QLabel(self.LABEL)
        layout.addWidget(self.status_label, 0)

        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            outfits = ek.parse_outfits(DATA_DIR)
            # Access SERIES_FN via the class so it isn't bound to the instance.
            series = type(self).SERIES_FN(outfits)
            self._bridge.loaded.emit((outfits, series))
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self._bridge.failed.emit(str(exc))

    def _load_error(self, message):
        self.status_label.setText("Error: {}".format(message))

    def _build_ui(self, payload):
        outfits, series = payload
        self.status_label.hide()

        tabs = QTabWidget()
        self.layout().addWidget(tabs, 1)

        for name in series:
            cls = type(self.TABLE_CLS.__name__ + name.replace(" ", ""),
                       (self.TABLE_CLS,), {"SERIES": name})
            app = cls()
            app.SERIES_OUTFITS = outfits
            self.apps[name] = app
            tabs.addTab(app, name)
