"""Endless Sky data tools: a Qt GUI for browsing and comparing game data.

Modules are split by responsibility:

* ``paths``         - repo/data/plugin path constants
* ``config``        - app-wide data policy (e.g. zero-cost exclusion)
* ``parse``         - Endless Sky data-file parsing helpers
* ``ships``         - ship bunk-capacity rows + ship table columns
* ``outfits``       - generator/engine/weapon rows + their table columns
* ``images``        - locating outfit/ship sprites (incl. high-DPI plugin art)
* ``theme``         - shared dark palette and Qt stylesheet
* ``table``         - the reusable heatmap table (QTableView + model + delegate)
* ``engine_picker`` - the engine knapsack solver tab
* ``outfit_apps``   - Generators / Engines / Ship Bunks tabs
* ``weapons``       - the weapon-type comparison tab

Run it with the entry script at ``knapsack/endless_sky_tools.py`` (or
``python -m es_tools`` from inside the ``knapsack`` folder).
"""

import sys

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from .engine_picker import EnginePickerApp
from .outfit_apps import EnginesApp, GeneratorsApp, ShipBunksApp
from .theme import apply_theme
from .weapons import WeaponsApp

GEOMETRY_KEY = "window/geometry"


class MainWindow(QMainWindow):
    """Top-level window holding one tab per tool."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Endless Sky Tools")
        self.resize(1120, 680)

        tabs = QTabWidget()
        tabs.addTab(EnginePickerApp(), "Engine Picker")
        tabs.addTab(ShipBunksApp(), "Ship Bunks")
        tabs.addTab(GeneratorsApp(), "Generators")
        tabs.addTab(EnginesApp(), "Engines")
        tabs.addTab(WeaponsApp(), "Weapons")
        self.setCentralWidget(tabs)

    def closeEvent(self, event):
        """Persist position, size, and maximized/full-screen state."""
        QSettings().setValue(GEOMETRY_KEY, self.saveGeometry())
        super().closeEvent(event)


def restore_window(window):
    """Restore the window's previous geometry and window state, if any."""
    geometry = QSettings().value(GEOMETRY_KEY)
    if isinstance(geometry, QByteArray) and not geometry.isEmpty():
        window.restoreGeometry(geometry)
        if window.isFullScreen():
            window.showFullScreen()
        elif window.isMaximized():
            window.showMaximized()
        else:
            window.show()
        return
    window.show()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("EndlessSky")
    app.setApplicationName("Endless Sky Tools")
    apply_theme(app)

    window = MainWindow()
    restore_window(window)
    sys.exit(app.exec())
