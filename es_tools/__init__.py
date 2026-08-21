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

import os
import sys

from PySide6.QtCore import QByteArray, QSettings, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                               QToolButton)

from .engine_picker import EnginePickerApp
from .outfit_apps import (EnginesApp, HandToHandApp, PowerApp, ShipBunksApp,
                          SpecialApp)
from .paths import ICONS_DIR
from .systems import SystemsApp
from .theme import apply_theme
from .weapons import WeaponsApp

GEOMETRY_KEY = "window/geometry"
TAB_KEY = "window/tab_state"


def _collect_tabs(tabs, path="", state=None, visited=None):
    """Return {tab_path: current_index} for this tab widget and all nested ones.

    ``path`` is a slash-separated list of child indices locating each tab
    widget, e.g. the Weapons "Guns / Projectiles" sub-tab is ``"3/1/1"``.
    """
    if state is None:
        state, visited = {}, set()
    if id(tabs) in visited:
        return state
    visited.add(id(tabs))
    state[path] = tabs.currentIndex()
    for i in range(tabs.count()):
        for sub in tabs.widget(i).findChildren(QTabWidget):
            _collect_tabs(sub, "{}/{}".format(path, i) if path else str(i),
                          state, visited)
    return state


def _restore_tabs(tabs, state, path="", visited=None):
    """Set each tab widget's current index back to its previously saved one."""
    if not isinstance(state, dict):
        return
    if visited is None:
        visited = set()
    if id(tabs) in visited:
        return
    visited.add(id(tabs))
    index = state.get(path)
    if isinstance(index, int) and 0 <= index < tabs.count():
        tabs.setCurrentIndex(index)
    for i in range(tabs.count()):
        for sub in tabs.widget(i).findChildren(QTabWidget):
            _restore_tabs(sub, state, "{}/{}".format(path, i) if path else str(i),
                          visited)


class MainWindow(QMainWindow):
    """Top-level window holding one tab per tool."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Endless Sky Tools")
        self.resize(1120, 680)

        tabs = QTabWidget()
        tabs.addTab(EnginePickerApp(), "Engine Picker")
        tabs.addTab(ShipBunksApp(), "Ship Bunks")
        tabs.addTab(EnginesApp(), "Engines")
        tabs.addTab(PowerApp(), "Power")
        tabs.addTab(SystemsApp(), "Systems")
        tabs.addTab(WeaponsApp(), "Weapons")
        tabs.addTab(HandToHandApp(), "Hand to Hand")
        tabs.addTab(SpecialApp(), "Special")
        self.setCentralWidget(tabs)
        self.tabs = tabs

        # Restart button on the right end of the tab bar (after the last tab):
        # stops this process and starts a fresh one so modified code is
        # re-imported.
        self.restart_btn = QToolButton(self)
        self.restart_btn.setText("Restart")
        self.restart_btn.setToolTip("Stop and restart the app to reapply "
                                    "modified code.")
        self.restart_btn.clicked.connect(self.restart_app)
        tabs.setCornerWidget(self.restart_btn, Qt.Corner.TopRightCorner)

    def restart_app(self):
        """Stop the program and restart it to reapply modified code."""
        # Persist window geometry and tab selection before we disappear.
        self.close()
        QApplication.processEvents()
        cmd = [sys.executable] + sys.argv
        try:
            os.execv(sys.executable, cmd)
        except OSError:  # pragma: no cover - execv can fail on some platforms.
            import subprocess
            subprocess.Popen(cmd)
            os._exit(0)

    def closeEvent(self, event):
        """Persist position, size, window state, and the selected tab(s)."""
        QSettings().setValue(GEOMETRY_KEY, self.saveGeometry())
        if self.tabs is not None:
            QSettings().setValue(TAB_KEY, _collect_tabs(self.tabs))
        super().closeEvent(event)


def restore_window(window):
    """Restore the window's previous geometry, window state, and tabs."""
    geometry = QSettings().value(GEOMETRY_KEY)
    if isinstance(geometry, QByteArray) and not geometry.isEmpty():
        window.restoreGeometry(geometry)
        if window.isFullScreen():
            window.showFullScreen()
        elif window.isMaximized():
            window.showMaximized()
        else:
            window.show()
    else:
        window.show()
    _restore_tabs_async(window, QSettings().value(TAB_KEY))


def _restore_tabs_async(window, state):
    """Restore the saved tab selection once all async sub-tabs are built.

    Nested sub-tabs (series/weapon-type tabs) are created on worker threads
    after the window shows, so they may not exist when ``restore_window`` first
    runs. Retry until the number of tab widgets matches the saved state.
    """
    if not isinstance(state, dict) or not state:
        return
    expected = len(state)
    attempts = [0]

    def attempt():
        attempts[0] += 1
        _restore_tabs(window.tabs, state)
        if len(_collect_tabs(window.tabs)) >= expected or attempts[0] >= 60:
            timer.stop()

    timer = QTimer(window)
    timer.setInterval(150)
    timer.timeout.connect(attempt)
    timer.start()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("EndlessSky")
    app.setApplicationName("Endless Sky Tools")

    # Reuse the game's Windows icon (the same one embedded in EndlessSky.exe).
    icon_path = os.path.join(ICONS_DIR, "WinApp.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    apply_theme(app)

    window = MainWindow()
    restore_window(window)
    sys.exit(app.exec())
