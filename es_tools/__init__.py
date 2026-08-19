"""Endless Sky data tools: a tkinter GUI for browsing and comparing game data.

Modules are split by responsibility so pieces can be refactored independently:

* ``paths``         - repo/data/plugin path constants
* ``parse``         - Endless Sky data-file parsing helpers
* ``ships``         - ship bunk-capacity rows + ship table columns
* ``outfits``       - generator/engine/weapon rows + their table columns
* ``images``        - locating outfit/ship sprites (incl. high-DPI plugin art)
* ``theme``         - shared dark colors and ttk styling
* ``table``         - the reusable heatmap table (OutfitTableApp)
* ``engine_picker`` - the engine knapsack solver tab
* ``outfit_apps``   - Generators / Engines / Ship Bunks tabs
* ``weapons``       - the weapon-type comparison tab

Run it with the entry script at ``knapsack/endless_sky_tools.py`` (or
``python -m es_tools`` from inside the ``knapsack`` folder).
"""

import tkinter as tk
from tkinter import ttk

from .engine_picker import EnginePickerApp
from .outfit_apps import EnginesApp, GeneratorsApp, ShipBunksApp
from .theme import apply_theme
from .weapons import WeaponsApp


def main():
    root = tk.Tk()
    root.title("Endless Sky Tools")
    root.geometry("1120x680")

    apply_theme(root)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    engine_tab = ttk.Frame(notebook)
    engine_app = EnginePickerApp(engine_tab)
    engine_app.pack(fill=tk.BOTH, expand=True)
    notebook.add(engine_tab, text="Engine Picker")

    bunks_tab = ttk.Frame(notebook)
    bunks_app = ShipBunksApp(bunks_tab)
    bunks_app.pack(fill=tk.BOTH, expand=True)
    notebook.add(bunks_tab, text="Ship Bunks")

    generators_tab = ttk.Frame(notebook)
    generators_app = GeneratorsApp(generators_tab)
    generators_app.pack(fill=tk.BOTH, expand=True)
    notebook.add(generators_tab, text="Generators")

    engines_tab = ttk.Frame(notebook)
    engines_app = EnginesApp(engines_tab)
    engines_app.pack(fill=tk.BOTH, expand=True)
    notebook.add(engines_tab, text="Engines")

    weapons_tab = ttk.Frame(notebook)
    weapons_app = WeaponsApp(weapons_tab)
    weapons_app.pack(fill=tk.BOTH, expand=True)
    notebook.add(weapons_tab, text="Weapons")

    def on_close():
        generators_app._on_close()
        engine_app._on_close()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.bind("<Configure>", engine_app._on_configure)

    def on_up(event):
        selected = notebook.select()
        if selected and notebook.index(selected) == 0:
            engine_app._on_up(event)

    def on_down(event):
        selected = notebook.select()
        if selected and notebook.index(selected) == 0:
            engine_app._on_down(event)

    root.bind("<Up>", on_up)
    root.bind("<Down>", on_down)

    root.mainloop()
