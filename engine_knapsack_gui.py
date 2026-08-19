#!/usr/bin/env python3
"""A tkinter GUI for Endless Sky data tools.

Run from the repository root (or anywhere) with:

    python knapsack/engine_knapsack_gui.py

The window has four tabs:

  * "Engine Picker" - lists every non-dominated (thrust, turn) combination,
    each with two small bars: blue for forward thrust and orange for turning.
    Click a row to see the exact engine list on the right.

  * "Ship Bunks" - lists every ship by its maximum achievable crew capacity,
    showing the ship sprite next to the table.

  * "Generators" - compares the stats of every generator outfit, showing the
    outfit thumbnail next to the table.

  * "Engines" - compares the stats of every engine outfit.
"""

import json
import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_knapsack as ek

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "data"))
IMAGES_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "images"))

# Dark theme colors shared by both tabs.
BG = "#1e1e1e"
FG = "#e0e0e0"
ENTRY_BG = "#2d2d2d"
SELECT_BG = "#264f78"

# Outfit effects used by the ship bunks calculation.
EXPANSION_OUTFIT_SPACE = 15.0
EXPANSION_CARGO_SPACE = 20.0
BUNK_ROOM_BUNKS = 4.0
BUNK_ROOM_OUTFIT_SPACE = 20.0

# Ship bunks table columns: (header, row key, width, anchor).
SHIP_COLUMNS = [
    ("Source Name", "name", 170, "w"),
    ("In-Game Name", "display_name", 170, "w"),
    ("Max Bunks", "max_bunks", 90, "e"),
    ("Bunks", "bunks", 70, "e"),
    ("Cargo", "cargo", 70, "e"),
    ("Outfit", "outfit", 70, "e"),
    ("Expansions", "expansions", 90, "e"),
    ("Outfit Total", "outfit_total", 90, "e"),
    ("Bunk Rooms", "bunk_rooms", 90, "e"),
    ("Leftover Outfit", "leftover_outfit", 110, "e"),
    ("Category", "category", 150, "w"),
    ("Cost", "cost", 90, "e"),
    ("Shields", "shields", 80, "e"),
    ("Hull", "hull", 70, "e"),
    ("Crew", "crew", 60, "e"),
]

# Generator comparison table columns: (header, row key, width, anchor).
GENERATOR_COLUMNS = [
    ("Name", "name", 180, "w"),
    ("Faction", "faction", 110, "w"),
    ("Cost", "cost", 90, "e"),
    ("Mass", "mass", 70, "e"),
    ("Space", "space", 70, "e"),
    ("Energy/s", "energy", 80, "e"),
    ("Heat/s", "heat", 70, "e"),
    ("Energy/Space", "energy_per_space", 100, "e"),
    ("Energy/Heat", "energy_per_heat", 100, "e"),
]

# Engine comparison table columns: (header, row key, width, anchor).
ENGINE_COLUMNS = [
    ("Name", "name", 190, "w"),
    ("Faction", "faction", 110, "w"),
    ("Cost", "cost", 90, "e"),
    ("Mass", "mass", 70, "e"),
    ("Space", "space", 70, "e"),
    ("Thrust", "thrust", 80, "e"),
    ("Turn", "turn", 80, "e"),
    ("Energy/s", "energy", 90, "e"),
    ("Heat/s", "heat", 70, "e"),
    ("Thrust/Space", "thrust_per_space", 100, "e"),
    ("Turn/Space", "turn_per_space", 100, "e"),
]


def tokenize(line):
    """Split a data-file line into tokens, honoring quoted strings.

    Endless Sky uses double quotes for most strings and backticks when a
    string itself needs to contain double quotes.
    """
    tokens = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c in " \t":
            i += 1
            continue
        if c in ('"', '`'):
            quote = c
            j = i + 1
            while j < n and line[j] != quote:
                j += 1
            tokens.append(line[i + 1:j])
            i = j + 1
        else:
            j = i
            while j < n and line[j] not in " \t":
                j += 1
            tokens.append(line[i:j])
            i = j
    return tokens


def indent(line):
    """Return the tab indentation level of a line."""
    return len(line) - len(line.lstrip("\t"))


def parse_value(token):
    """Return the token as a float when possible, otherwise as a string."""
    try:
        return float(token)
    except ValueError:
        return token


def data_files(data_dir):
    """Yield the data files to scan, skipping the deprecated folder."""
    for root, dirs, files in os.walk(data_dir):
        if os.path.basename(root) == "_deprecated":
            continue
        for name in sorted(files):
            if name.endswith(".txt"):
                yield os.path.join(root, name)


def parse_blocks(data_dir):
    """Parse all ship definitions into base/variant blocks with attribute ops."""
    blocks = []
    for path in data_files(data_dir):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            level = indent(line)
            tokens = tokenize(line)

            if level == 0 and len(tokens) >= 2 and tokens[0] == "ship":
                base = tokens[1]
                variant = tokens[2] if len(tokens) >= 3 else None
                ops = []
                i += 1

                # Consume this ship's block (all lines indented under it).
                while i < n and indent(lines[i]) > 0:
                    inner_level = indent(lines[i])
                    inner = tokenize(lines[i])

                    if inner_level == 1 and inner:
                        if inner[0] in ("sprite", "thumbnail", "display name", "plural") and len(inner) >= 2:
                            ops.append(("set", {inner[0]: inner[1]}))
                            i += 1
                            continue

                        if inner[0] == "attributes":
                            values = {}
                            ops.append(("set", values))
                            i += 1
                            while i < n and indent(lines[i]) > 1:
                                attr_level = indent(lines[i])
                                attr = tokenize(lines[i])
                                if attr_level == 2 and len(attr) >= 2:
                                    values[attr[0]] = parse_value(attr[1])
                                i += 1
                            continue

                        if inner[0] == "add" and len(inner) >= 2 and inner[1] == "attributes":
                            values = {}
                            ops.append(("add", values))
                            i += 1
                            while i < n and indent(lines[i]) > 1:
                                attr_level = indent(lines[i])
                                attr = tokenize(lines[i])
                                if attr_level == 2 and len(attr) >= 2:
                                    values[attr[0]] = parse_value(attr[1])
                                i += 1
                            continue

                    i += 1

                blocks.append({"base": base, "variant": variant, "ops": ops})
            else:
                i += 1

    return blocks


def apply_ops(attrs, ops):
    """Apply a block's attribute operations to the given attribute dict."""
    for mode, values in ops:
        if mode == "set":
            attrs.update(values)
        else:  # "add"
            for key, value in values.items():
                if isinstance(value, float) and isinstance(attrs.get(key), float):
                    attrs[key] += value
                else:
                    attrs[key] = value


def resolve_ships(blocks):
    """Resolve bases first, then variants, returning name/attribute rows."""
    base_attrs = {}

    # Bases must exist before variants can inherit from them.
    for block in blocks:
        if block["variant"] is None:
            attrs = {}
            apply_ops(attrs, block["ops"])
            base_attrs[block["base"]] = attrs

    ships = []
    for block in blocks:
        attrs = {}
        if block["variant"] is not None:
            attrs = base_attrs.get(block["base"], {}).copy()
        apply_ops(attrs, block["ops"])

        name = block["variant"] if block["variant"] is not None else block["base"]
        ships.append({"name": name, "base": block["base"],
                      "variant": block["variant"], "attrs": attrs})

    return ships


def number(attrs, key):
    """Get a numeric attribute, defaulting to zero."""
    value = attrs.get(key, 0.0)
    return value if isinstance(value, float) else 0.0


def build_rows(ships):
    """Compute the derived columns for every ship."""
    rows = []
    for ship in ships:
        attrs = ship["attrs"]
        cargo = max(0.0, number(attrs, "cargo space"))
        outfit = max(0.0, number(attrs, "outfit space"))
        bunks = max(0.0, number(attrs, "bunks"))

        expansions = int(cargo // EXPANSION_CARGO_SPACE)
        outfit_total = outfit + expansions * EXPANSION_OUTFIT_SPACE
        bunk_rooms = int(outfit_total // BUNK_ROOM_OUTFIT_SPACE)
        max_bunks = bunks + bunk_rooms * BUNK_ROOM_BUNKS

        category = attrs.get("category", "")
        sprite = attrs.get("sprite", "")
        thumbnail = attrs.get("thumbnail", "")
        display_name = attrs.get("display name", "")
        if not isinstance(display_name, str) or not display_name:
            display_name = ship["base"] if ship["variant"] is not None else ship["name"]
        rows.append({
            "name": ship["name"],
            "display_name": display_name,
            "is_base": ship["variant"] is None,
            "category": category if isinstance(category, str) else "",
            "cost": number(attrs, "cost"),
            "shields": number(attrs, "shields"),
            "hull": number(attrs, "hull"),
            "crew": number(attrs, "required crew"),
            "bunks": bunks,
            "cargo": cargo,
            "outfit": outfit,
            "expansions": expansions,
            "outfit_total": outfit_total,
            "bunk_rooms": bunk_rooms,
            "max_bunks": max_bunks,
            "leftover_outfit": outfit_total - bunk_rooms * BUNK_ROOM_OUTFIT_SPACE,
            "sprite": sprite if isinstance(sprite, str) else "",
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["max_bunks"], row["name"].lower()))
    return rows


def dedupe_rows(rows):
    """Merge rows whose displayed table columns are identical.

    The table ignores loadouts and also hides some attributes (drag, fuel,
    weapon/engine capacity, mass, etc.), so ships that differ only in those
    hidden stats are still considered the same ship here. The merged row keeps
    the base ship's name (or the alphabetically first variant name when the
    group only contains variants).
    """
    key_columns = [key for _, key, _, _ in SHIP_COLUMNS if key != "name"]

    groups = {}
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        groups.setdefault(key, []).append(row)

    merged = []
    for group in groups.values():
        representative = None
        for row in group:
            if row.get("is_base"):
                representative = row
                break
        if representative is None:
            representative = min(group, key=lambda row: row["name"])
        merged.append(dict(representative))

    return merged


def build_generator_rows(outfits):
    """Return one row per generator outfit with comparable stats."""
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("series") != "Generators":
            continue

        energy = number(attrs, "energy generation")
        heat = number(attrs, "heat generation")
        space = max(0.0, -number(attrs, "outfit space"))
        mass = number(attrs, "mass")
        cost = number(attrs, "cost")
        thumbnail = attrs.get("thumbnail", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "cost": cost,
            "mass": mass,
            "space": space,
            "energy": energy,
            "heat": heat,
            "energy_per_space": energy / space if space > 0 else 0.0,
            "energy_per_heat": energy / heat if heat > 0 else 0.0,
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["energy"], row["name"].lower()))
    return rows


def build_engine_rows(outfits):
    """Return one row per engine outfit with comparable stats."""
    rows = []
    for outfit in outfits:
        attrs = outfit["attrs"]
        if attrs.get("series") != "Engines":
            continue

        thrust = number(attrs, "thrust")
        turn = number(attrs, "turn")
        if thrust == 0.0 and turn == 0.0:
            continue

        cost = number(attrs, "cost")
        mass = number(attrs, "mass")
        space = max(0.0, -number(attrs, "outfit space"),
                    -number(attrs, "engine capacity"))
        energy = number(attrs, "thrusting energy") + number(attrs, "turning energy")
        heat = number(attrs, "thrusting heat") + number(attrs, "turning heat")
        thumbnail = attrs.get("thumbnail", "")

        rows.append({
            "name": outfit["name"],
            "faction": outfit["faction"],
            "cost": cost,
            "mass": mass,
            "space": space,
            "thrust": thrust,
            "turn": turn,
            "energy": energy,
            "heat": heat,
            "thrust_per_space": thrust / space if space > 0 else 0.0,
            "turn_per_space": turn / space if space > 0 else 0.0,
            "thumbnail": thumbnail if isinstance(thumbnail, str) else "",
        })

    rows.sort(key=lambda row: (-row["thrust"], row["name"].lower()))
    return rows


def format_number(value):
    """Format a numeric value with thousands separators and no decimal noise."""
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.1f}"


def format_ratio(value):
    """Format a derived ratio with a few decimal places."""
    return "{:.3f}".format(value).rstrip("0").rstrip(".")


def find_plugin_images_dir():
    """Locate the images folder of the first plugin that ships game images."""
    plugins_dir = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "plugins"))
    if not os.path.isdir(plugins_dir):
        return None
    for name in sorted(os.listdir(plugins_dir)):
        images = os.path.normpath(os.path.join(plugins_dir, name, "images"))
        if os.path.isdir(images):
            return images
    return None


def apply_theme(root):
    """Apply the shared dark theme to all ttk widgets."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # The root window shows through the spacing around the paned window, so
    # it must be dark as well, or thin white strips appear at the edges.
    root.configure(bg=BG)

    style.configure(".", background=BG, foreground=FG,
                    fieldbackground=ENTRY_BG)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TButton", background="#333333", foreground=FG,
                    borderwidth=1, focusthickness=1, focuscolor=BG)
    style.map("TButton",
              background=[("active", "#3c3c3c"), ("pressed", "#2a2a2a")])
    style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG,
                    insertcolor=FG)
    style.configure("TCheckbutton", background=BG, foreground=FG)
    style.map("TCheckbutton",
              background=[("active", BG)],
              foreground=[("active", FG)])
    style.configure("TPanedwindow", background=BG)
    style.configure("Treeview", background=ENTRY_BG,
                    fieldbackground=ENTRY_BG, foreground=FG,
                    borderwidth=0, rowheight=24)
    style.configure("Treeview.Heading", background="#2d2d2d",
                    foreground=FG, borderwidth=0)
    style.map("Treeview.Heading",
              background=[("active", "#3a3a3a"), ("pressed", "#2a2a2a")],
              foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
    style.map("Treeview",
              background=[("selected", SELECT_BG)],
              foreground=[("selected", "#ffffff")])
    style.configure("TScrollbar", background="#3a3a3a",
                    troughcolor="#2d2d2d", bordercolor="#2d2d2d",
                    arrowcolor=FG)
    style.map("TScrollbar", background=[("active", "#4a4a4a")])
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background="#2d2d2d", foreground=FG,
                    padding=(12, 4))
    style.map("TNotebook.Tab",
              background=[("selected", BG), ("active", "#3a3a3a")],
              foreground=[("selected", "#ffffff")])


class EnginePickerApp(ttk.Frame):
    ROW_H = 30
    ENGINE_ROW_H = 168
    ENGINE_HEADER_H = 26
    THRUST_COLOR = "#4a90d9"
    TURN_COLOR = "#e08a4a"

    def __init__(self, master):
        super().__init__(master)
        self.root = master.winfo_toplevel()

        self.config_path = os.path.join(os.path.expanduser("~"),
                                        ".endless_sky_engine_picker.json")
        self._save_after_id = None
        self._load_config()

        self.data_dir = DATA_DIR
        self.outfits = None
        self.engines = []
        self.capacity = 0
        self.results = []
        self.selected = -1
        self.scroll = 0

        self.images_dir = IMAGES_DIR
        self._photo_cache = {}
        self.engine_rows = []
        self.engine_scroll = 0

        self.factions = []
        self.faction_vars = {}
        self._debounce_id = None
        self._computing = False
        self._pending = False

        self.bg = BG
        self.fg = FG
        self.entry_bg = ENTRY_BG
        self.select_bg = SELECT_BG
        self.mono_font = self._pick_mono_font()

        self._build_controls()
        self._build_faction_bar()
        self._build_panels()

        self._start_loading()

    def _pick_mono_font(self):
        """Return the Fira Code Nerd Font descriptor, or TkFixedFont."""
        families = set(tkfont.families(self.root))
        if "FiraCode Nerd Font" in families:
            return ("FiraCode Nerd Font", 9)
        if "Fira Code Nerd Font" in families:
            return ("Fira Code Nerd Font", 9)
        return "TkFixedFont"

    # --------------------------------------------------------- persistence
    def _load_config(self):
        self.config = {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                self.config = json.load(handle)
            geometry = self.config.get("geometry")
            if geometry:
                try:
                    self.root.geometry(geometry)
                except tk.TclError:
                    pass
        except (OSError, ValueError):
            self.config = {}

    def _on_configure(self, event):
        if self.root.state() != "normal":
            return
        if not self.faction_vars:
            return
        if self._save_after_id is not None:
            self.root.after_cancel(self._save_after_id)
        self._save_after_id = self.root.after(500, self._save_config)

    def _save_config(self):
        self._save_after_id = None
        try:
            capacity = int(self.capacity_var.get())
        except (ValueError, tk.TclError):
            capacity = 180

        data = {
            "geometry": self.root.geometry(),
            "capacity": capacity,
        }
        if self.faction_vars:
            data["factions"] = [name for name, var in self.faction_vars.items()
                                if var.get()]
        elif "factions" in self.config:
            data["factions"] = self.config["factions"]

        try:
            with open(self.config_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError:
            pass

    def _on_close(self):
        self._save_config()
        self.root.destroy()

    # ------------------------------------------------------------------ UI
    def _build_controls(self):
        bar = ttk.Frame(self, padding=8)
        bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(bar, text="Engine capacity:").pack(side=tk.LEFT)
        self.capacity_var = tk.StringVar(value=str(self.config.get("capacity", 180)))
        ttk.Entry(bar, textvariable=self.capacity_var, width=6).pack(
            side=tk.LEFT, padx=(4, 12))

        self.compute_btn = ttk.Button(bar, text="Compute", command=self.compute)
        self.compute_btn.pack(side=tk.LEFT, padx=12)
        self.compute_btn.config(state=tk.DISABLED)

        self.status_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT, padx=8)

    def _build_faction_bar(self):
        self.checkbox_frame = ttk.Frame(self, padding=(8, 0, 8, 4))
        self.checkbox_frame.pack(side=tk.TOP, fill=tk.X)

    def _build_panels(self):
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Left: canvas list of results, each row with thrust/turn bars.
        left = ttk.Frame(paned)
        self.canvas = tk.Canvas(left, width=340, background=self.bg,
                                highlightthickness=1, highlightbackground="#333333")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL,
                                       command=self._on_scrollbar)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        paned.add(left, weight=1)

        # Right: summary + engine list with thumbnails for the selected result.
        right = ttk.Frame(paned)
        self.summary_var = tk.StringVar(value="Select a result.")
        ttk.Label(right, textvariable=self.summary_var, padding=6).pack(
            side=tk.TOP, fill=tk.X)

        self.engine_canvas = tk.Canvas(right, background=self.bg,
                                       highlightthickness=0)
        self.engine_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                                padx=(6, 0), pady=6)
        engine_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL,
                                      command=self._on_engine_scrollbar)
        engine_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=6)
        self.engine_scrollbar = engine_scroll

        self.engine_canvas.bind("<MouseWheel>", self._on_engine_wheel)
        self.engine_canvas.bind("<Configure>", lambda e: self.redraw_engines())
        paned.add(right, weight=2)

    # -------------------------------------------------------------- actions
    def compute(self):
        if self._computing:
            self._pending = True
            return
        try:
            capacity = int(self.capacity_var.get())
        except ValueError:
            self.status_var.set("Capacity must be an integer.")
            return

        capacity = max(0, capacity)
        filters = self._current_filters()

        self._computing = True
        self._pending = False
        self.status_var.set("Computing...")
        self.compute_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._compute_worker,
                         args=(capacity, filters), daemon=True).start()

    def _current_filters(self):
        if not self.factions:
            return []
        checked = [name for name, var in self.faction_vars.items() if var.get()]
        if not checked:
            # A token that matches no faction name, yielding an empty result.
            return ["\u0000"]
        if len(checked) == len(self.factions):
            return []
        return checked

    def _start_loading(self):
        self.status_var.set("Loading outfits...")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            outfits = ek.parse_outfits(self.data_dir)
            engines = ek.build_engines(outfits, [])
            factions = sorted({engine["faction"] for engine in engines})
            self.root.after(0, self._load_done, outfits, factions)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._compute_error, str(exc))

    def _load_done(self, outfits, factions):
        self.outfits = outfits
        self._build_faction_checkboxes(factions)
        self.compute_btn.config(state=tk.NORMAL)
        self.status_var.set("")
        self.compute()

    def _build_faction_checkboxes(self, factions):
        for child in self.checkbox_frame.winfo_children():
            child.destroy()

        self.factions = factions
        self.faction_vars = {}

        if "factions" in self.config:
            saved = set(self.config["factions"])
            all_checked = False
        else:
            saved = set()
            all_checked = True

        columns = 6
        for index, name in enumerate(factions):
            var = tk.BooleanVar(value=all_checked or name in saved)
            var.trace_add("write", self._on_faction_toggled)
            self.faction_vars[name] = var
            check = ttk.Checkbutton(self.checkbox_frame, text=name, variable=var)
            check.grid(row=index // columns, column=index % columns,
                       sticky="w", padx=2, pady=1)

    def _on_faction_toggled(self, *args):
        self._save_config()
        self._schedule_compute()

    def _schedule_compute(self):
        if self._debounce_id is not None:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(200, self._run_compute)

    def _run_compute(self):
        self._debounce_id = None
        self.compute()

    def _compute_worker(self, capacity, filters):
        try:
            if self.outfits is None:
                self.outfits = ek.parse_outfits(self.data_dir)
            engines = ek.prune_engines(ek.build_engines(self.outfits, filters))
            if not engines:
                self.root.after(0, self._compute_done, [], [], capacity)
                return
            frontier = ek.compute_frontier(capacity, engines)
            results = [{
                "node": node,
                "thrust": node.thrust,
                "turn": node.turn,
                "weight": node.weight,
            } for node in frontier]
            self.root.after(0, self._compute_done, results, engines, capacity)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._compute_error, str(exc))

    def _compute_done(self, results, engines, capacity):
        self.results = results
        self.engines = engines
        self.capacity = capacity
        self.selected = self._balanced_index(results) if results else -1
        self.scroll = 0
        self.compute_btn.config(state=tk.NORMAL)
        if not results:
            self.status_var.set("No matching engines found.")
            self.engine_rows = []
            self.redraw_engines()
            self._update_engine_scrollbar()
        else:
            self.status_var.set("{} combinations.".format(len(results)))
        self._scroll_to_selected()
        self.redraw()
        self._update_scrollbar()
        if self.selected >= 0:
            self._show_engines(self.selected)
        self._save_config()

        self._computing = False
        if self._pending:
            self._pending = False
            self.compute()

    def _compute_error(self, message):
        self._computing = False
        self.compute_btn.config(state=tk.NORMAL)
        self.status_var.set("Error: {}".format(message))
        if self._pending:
            self._pending = False
            self.compute()

    def _balanced_index(self, results):
        """Return the result whose thrust and turn are most balanced."""
        if not results:
            return -1
        max_thrust = max(r["thrust"] for r in results) or 1.0
        max_turn = max(r["turn"] for r in results) or 1.0
        best = 0
        best_score = None
        for index, result in enumerate(results):
            score = abs(result["thrust"] / max_thrust - result["turn"] / max_turn)
            if best_score is None or score < best_score:
                best_score = score
                best = index
        return best

    # ------------------------------------------------------------- drawing
    def redraw(self):
        canvas = self.canvas
        canvas.delete("all")
        if not self.results:
            canvas.create_text(10, 10, anchor="nw", text="No results.", fill=self.fg)
            return

        max_thrust = max(r["thrust"] for r in self.results) or 1.0
        max_turn = max(r["turn"] for r in self.results) or 1.0

        width = max(120, canvas.winfo_width())
        bar_x = 76
        bar_width = max(30, width - bar_x - 14)
        y = 6 - self.scroll

        for index, result in enumerate(self.results):
            if y + self.ROW_H < 0:
                y += self.ROW_H
                continue
            if y > canvas.winfo_height():
                break

            if index == self.selected:
                canvas.create_rectangle(2, y, width - 2, y + self.ROW_H - 2,
                                        fill=self.select_bg, outline="")

            thrust_len = int(bar_width * result["thrust"] / max_thrust)
            turn_len = int(bar_width * result["turn"] / max_turn)

            canvas.create_text(6, y + 1, anchor="nw",
                               text="T {:6.1f}".format(result["thrust"]),
                               fill=self.fg, font=self.mono_font)
            canvas.create_rectangle(bar_x, y + 4, bar_x + thrust_len, y + 10,
                                    fill=self.THRUST_COLOR, outline="")

            canvas.create_text(6, y + 15, anchor="nw",
                               text="U {:6.1f}".format(result["turn"]),
                               fill=self.fg, font=self.mono_font)
            canvas.create_rectangle(bar_x, y + 18, bar_x + turn_len, y + 24,
                                    fill=self.TURN_COLOR, outline="")

            y += self.ROW_H

    def _show_engines(self, index):
        result = self.results[index]
        counts = ek._recipe(result["node"], self.engines)

        dual = []
        thrusters = []
        steering = []
        for count, engine in counts.values():
            entry = (count, engine, self._thumbnail(engine))
            if engine["thrust"] > 0 and engine["turn"] > 0:
                dual.append(entry)
            elif engine["thrust"] > 0:
                thrusters.append(entry)
            else:
                steering.append(entry)
        dual.sort(key=lambda entry: (-entry[1]["thrust"], -entry[1]["turn"]))
        thrusters.sort(key=lambda entry: (-entry[1]["thrust"], -entry[1]["weight"]))
        steering.sort(key=lambda entry: (-entry[1]["turn"], -entry[1]["weight"]))

        rows = []
        if dual:
            rows.append(("header", "Multi-use engines"))
            rows.extend(("engine", *entry) for entry in dual)
        if thrusters:
            rows.append(("header", "Thrusters"))
            rows.extend(("engine", *entry) for entry in thrusters)
        if steering:
            rows.append(("header", "Steering"))
            rows.extend(("engine", *entry) for entry in steering)

        self.engine_rows = rows
        self.engine_scroll = 0

        self.summary_var.set(
            "Thrust {:.2f}   Turn {:.2f}   Used {}   Unused {}".format(
                result["thrust"], result["turn"],
                result["weight"], self.capacity - result["weight"]))
        self.redraw_engines()
        self._update_engine_scrollbar()

    # ------------------------------------------------------ engine thumbnails
    def _thumbnail(self, engine):
        thumb = engine.get("thumbnail") or ""
        if not thumb:
            return None
        path = os.path.join(self.images_dir, thumb + ".png")
        if not os.path.exists(path):
            return None
        if path in self._photo_cache:
            return self._photo_cache[path]

        try:
            image = tk.PhotoImage(file=path)
        except tk.TclError:
            return None
        # Show the thumbnails at their native resolution so they stay crisp;
        # only shrink extremely large images to keep the rows a sensible size.
        # Never upscale, because PhotoImage.zoom() uses nearest-neighbor and
        # would make the sprites look pixelated.
        largest = max(image.width(), image.height())
        if largest > 160:
            factor = (largest + 159) // 160
            image = image.subsample(factor, factor)
        self._photo_cache[path] = image
        return image

    def redraw_engines(self):
        canvas = self.engine_canvas
        canvas.delete("all")
        if not self.engine_rows:
            canvas.create_text(10, 10, anchor="nw", text="Select a result.",
                               fill=self.fg)
            return

        width = max(120, canvas.winfo_width())
        y = 4 - self.engine_scroll
        for row in self.engine_rows:
            height = self.ENGINE_HEADER_H if row[0] == "header" else self.ENGINE_ROW_H
            if y + height < 0:
                y += height
                continue
            if y > canvas.winfo_height():
                break

            if row[0] == "header":
                canvas.create_text(8, y + 2, anchor="nw", text=row[1],
                                   fill="#7fb2dd", font=self.mono_font)
                canvas.create_line(8, y + 21, width - 8, y + 21, fill="#444444")
                y += height
                continue

            _, count, engine, photo = row
            center_y = y + self.ENGINE_ROW_H // 2
            if photo is not None:
                canvas.create_image(86, center_y, image=photo, anchor="center")
            else:
                canvas.create_rectangle(6, y + 4, 166, y + self.ENGINE_ROW_H - 4,
                                        fill="#3a3a3a", outline="#555555")

            line1 = "{}x {}  ({})".format(count, engine["name"], engine["faction"])
            line2 = "weight {:>3}   thrust {:>7.2f}   turn {:>7.2f}".format(
                engine["weight"], engine["thrust"], engine["turn"])
            canvas.create_text(176, y + 66, anchor="nw", text=line1, fill=self.fg)
            canvas.create_text(176, y + 88, anchor="nw", text=line2, fill="#b0b0b0")

            y += height

    def _on_engine_wheel(self, event):
        if not self.engine_rows:
            return
        step = -1 if event.delta > 0 else 1
        self.engine_scroll += step * 40
        self._clamp_engine_scroll()
        self.redraw_engines()
        self._update_engine_scrollbar()

    def _on_engine_scrollbar(self, action, *args):
        if not self.engine_rows:
            return
        total = self._max_engine_scroll()
        if action == "moveto":
            self.engine_scroll = int(float(args[0]) * total)
        elif action == "scroll":
            amount = int(args[1])
            if args[2] == "units":
                self.engine_scroll += amount * 40
            else:
                self.engine_scroll += amount * max(1, self.engine_canvas.winfo_height())
        self._clamp_engine_scroll()
        self.redraw_engines()
        self._update_engine_scrollbar()

    def _engine_content_height(self):
        return sum(self.ENGINE_HEADER_H if row[0] == "header" else self.ENGINE_ROW_H
                   for row in self.engine_rows)

    def _max_engine_scroll(self):
        return max(0, self._engine_content_height() - self.engine_canvas.winfo_height())

    def _clamp_engine_scroll(self):
        self.engine_scroll = max(0, min(self.engine_scroll, self._max_engine_scroll()))

    def _update_engine_scrollbar(self):
        total = self._max_engine_scroll()
        if total <= 0:
            self.engine_scrollbar.set(0.0, 1.0)
            return
        first = self.engine_scroll / total
        last = (self.engine_scroll + self.engine_canvas.winfo_height()) / total
        self.engine_scrollbar.set(first, min(1.0, last))

    # -------------------------------------------------------------- events
    def _on_click(self, event):
        if not self.results:
            return
        index = int((event.y + self.scroll) // self.ROW_H)
        if 0 <= index < len(self.results):
            self.selected = index
            self.redraw()
            self._show_engines(index)

    def _on_up(self, event):
        self._move_selection(-1)

    def _on_down(self, event):
        self._move_selection(1)

    def _move_selection(self, delta):
        if not self.results:
            return
        self.selected = max(0, min(len(self.results) - 1, self.selected + delta))
        self._scroll_to_selected()
        self.redraw()
        self._update_scrollbar()
        self._show_engines(self.selected)

    def _scroll_to_selected(self):
        if not self.results or self.selected < 0:
            return
        # Center the selected row in the visible area (clamped to the list).
        height = self.canvas.winfo_height()
        row_center = 6 + self.selected * self.ROW_H + self.ROW_H / 2.0
        self.scroll = int(row_center - height / 2.0)
        self.scroll = max(0, min(self.scroll, self._max_scroll()))

    def _on_wheel(self, event):
        if not self.results:
            return
        step = -1 if event.delta > 0 else 1
        self.scroll += step * self.ROW_H
        self._clamp_scroll()
        self.redraw()
        self._update_scrollbar()

    def _on_scrollbar(self, action, *args):
        if not self.results:
            return
        total = self._max_scroll()
        if action == "moveto":
            self.scroll = int(float(args[0]) * total)
        elif action == "scroll":
            amount = int(args[1])
            if args[2] == "units":
                self.scroll += amount * self.ROW_H
            else:
                self.scroll += amount * max(1, self.canvas.winfo_height())
        self._clamp_scroll()
        self.redraw()
        self._update_scrollbar()

    def _max_scroll(self):
        visible = self.canvas.winfo_height()
        content = len(self.results) * self.ROW_H
        return max(0, content - visible)

    def _clamp_scroll(self):
        self.scroll = max(0, min(self.scroll, self._max_scroll()))

    def _update_scrollbar(self):
        total = self._max_scroll()
        if total <= 0:
            self.scrollbar.set(0.0, 1.0)
            return
        first = self.scroll / total
        last = (self.scroll + self.canvas.winfo_height()) / total
        self.scrollbar.set(first, min(1.0, last))


class OutfitTableApp(ttk.Frame):
    """Reusable heatmap table for comparing outfit stats."""

    COLUMNS = []
    BUILDER = None
    REVERSED_KEYS = set()
    RATIO_KEYS = set()
    NOUN = "outfit"
    CONFIG_FILENAME = ".endless_sky_outfits.json"
    DEFAULT_SORT_KEY = "name"
    DEFAULT_SORT_REVERSE = False
    TEXT_KEYS = {"name", "faction"}
    HAS_FACTIONS = True
    HAS_SHOW_ALL = False

    ROW_H = 24
    HEADER_H = 26

    def __init__(self, master):
        super().__init__(master)
        self.root = master.winfo_toplevel()

        self.config_path = os.path.join(os.path.expanduser("~"),
                                        self.CONFIG_FILENAME)
        self._load_config()

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
        self._photo_cache = {}
        self._path_cache = {}
        self._current_photo = None
        self._current_row = None
        self.show_all_var = None
        self._sort_key = self.DEFAULT_SORT_KEY
        self._sort_reverse = self.DEFAULT_SORT_REVERSE
        self.preview_size = 240
        self._preload_paths = []
        self._preload_index = 0
        self._preload_attempted = set()
        self.numeric_keys = [key for _, key, _, _ in self.COLUMNS
                             if key not in self.TEXT_KEYS]
        self.reversed_keys = self.REVERSED_KEYS
        self.selected = -1
        self.y_offset = 0
        self.x_offset = 0
        self._col_layout = []
        self._content_width = 0
        self._scales = {}
        self._decimals = {}
        self._redraw_scheduled = False
        self._configure_after_id = None

        self._build_ui()
        self._start_loading()

    def _load_config(self):
        self.config = {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                self.config = json.load(handle)
        except (OSError, ValueError):
            self.config = {}

    def _save_config(self):
        data = {}
        if self.HAS_FACTIONS:
            if self.faction_vars:
                data["factions"] = [name for name, var in self.faction_vars.items()
                                    if var.get()]
            elif "factions" in self.config:
                data["factions"] = self.config["factions"]
        if self.HAS_SHOW_ALL and self.show_all_var is not None:
            data["show_all"] = bool(self.show_all_var.get())
        try:
            with open(self.config_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError:
            pass

    def _on_close(self):
        self._save_config()

    def _build_ui(self):
        bar = ttk.Frame(self, padding=8)
        bar.pack(side=tk.TOP, fill=tk.X)

        self.status_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT, padx=8)

        self._build_extra_bar(bar)
        if self.HAS_FACTIONS:
            self._build_faction_bar()

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Left: canvas heatmap table of outfits.
        table_frame = ttk.Frame(paned)
        self.table_canvas = tk.Canvas(table_frame, background=ENTRY_BG,
                                      highlightthickness=0)
        self.y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL,
                                      command=self._on_y_scrollbar)
        self.x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL,
                                      command=self._on_x_scrollbar)

        self.table_canvas.grid(row=0, column=0, sticky="nsew")
        self.y_scroll.grid(row=0, column=1, sticky="ns")
        self.x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        paned.add(table_frame, weight=3)

        x = 0
        for header, key, width, anchor in self.COLUMNS:
            self._col_layout.append((key, x, width, anchor))
            x += width
        self._content_width = x

        self.table_canvas.bind("<Configure>", self._on_table_configure)
        self.table_canvas.bind("<MouseWheel>", self._on_wheel)
        self.table_canvas.bind("<Button-1>", self._on_click)
        self.table_canvas.bind("<Button-3>", self._on_right_click)
        self.table_canvas.bind("<Up>", lambda event: self._move_selection(-1))
        self.table_canvas.bind("<Down>", lambda event: self._move_selection(1))
        self.table_canvas.bind("<Prior>",
                               lambda event: self._move_selection(-self._page_size()))
        self.table_canvas.bind("<Next>",
                               lambda event: self._move_selection(self._page_size()))

        # Right: outfit thumbnail preview.
        preview = ttk.Frame(paned, padding=6)
        self.name_var = tk.StringVar(value="")
        ttk.Label(preview, textvariable=self.name_var,
                  font=("TkDefaultFont", 11, "bold")).pack(side=tk.TOP,
                                                           anchor="w")

        self.canvas = tk.Canvas(preview, background=BG, width=260,
                                highlightthickness=1,
                                highlightbackground="#333333")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=6)

        self.stats_var = tk.StringVar(value="")
        ttk.Label(preview, textvariable=self.stats_var,
                  justify=tk.LEFT).pack(side=tk.TOP, anchor="w")
        paned.add(preview, weight=2)

        self.canvas.bind("<Configure>", lambda event: self._redraw_preview())

        self.context_menu = tk.Menu(self.table_canvas, tearoff=0,
                                    background=ENTRY_BG, foreground=FG,
                                    activebackground=SELECT_BG,
                                    activeforeground="#ffffff")
        self._build_context_menu(self.context_menu)

    def _start_loading(self):
        self.status_var.set("Loading {}s...".format(self.NOUN))
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            outfits = ek.parse_outfits(self.data_dir)
            rows = type(self).BUILDER(outfits)
            self.root.after(0, self._on_data_loaded, outfits, rows)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._load_error, str(exc))

    def _on_data_loaded(self, outfits, rows):
        self.outfits = outfits
        self.all_rows = rows
        if self.HAS_FACTIONS:
            self._build_faction_checkboxes(sorted({row["faction"] for row in rows}))
        self._refresh_rows()

    def _load_error(self, message):
        self.status_var.set("Error: {}".format(message))

    def _build_faction_bar(self):
        self.checkbox_frame = ttk.Frame(self, padding=(8, 0, 8, 4))
        self.checkbox_frame.pack(side=tk.TOP, fill=tk.X)

    def _build_faction_checkboxes(self, factions):
        for child in self.checkbox_frame.winfo_children():
            child.destroy()

        self.factions = factions
        self.faction_vars = {}

        if "factions" in self.config:
            saved = set(self.config["factions"])
        else:
            saved = None

        columns = 6
        for index, name in enumerate(factions):
            var = tk.BooleanVar(value=(saved is None or name in saved))
            var.trace_add("write", self._on_faction_toggled)
            self.faction_vars[name] = var
            check = ttk.Checkbutton(self.checkbox_frame, text=name, variable=var)
            check.grid(row=index // columns, column=index % columns,
                       sticky="w", padx=2, pady=1)

    def _on_faction_toggled(self, *args):
        self._save_config()
        self._refresh_rows()

    def _current_factions(self):
        if not self.factions:
            return None
        checked = {name for name, var in self.faction_vars.items() if var.get()}
        if not checked:
            return set()
        if len(checked) == len(self.factions):
            return None
        return checked

    def _refresh_rows(self):
        base = self._base_rows()
        filters = self._current_factions()
        if filters is None:
            self.rows = list(base)
        else:
            self.rows = [row for row in base if row["faction"] in filters]
        self._apply_sort()
        self._recompute_columns()
        self._select_first()
        self._start_preload()

    def _on_sort(self, key):
        if self._sort_key == key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_key = key
            self._sort_reverse = key not in self.TEXT_KEYS
        self._apply_sort()
        self._select_first()

    def _apply_sort(self):
        key = self._sort_key
        reverse = self._sort_reverse

        def sort_value(row):
            value = row.get(key, "")
            return value.lower() if isinstance(value, str) else value

        self.rows.sort(key=sort_value, reverse=reverse)

    def _select_first(self):
        if self.rows:
            self.selected = 0
            self._show_preview(self.rows[0])
        else:
            self.selected = -1
            self._current_row = None
            self.name_var.set("")
            self.stats_var.set("")
            self._redraw_preview()
        self.y_offset = 0
        self._update_scrollbars()
        self._redraw_table()

    def _select(self, index):
        if index < 0 or index >= len(self.rows):
            return
        self.selected = index
        self.table_canvas.focus_set()
        self._show_preview(self.rows[index])
        self._redraw_table()

    def _move_selection(self, delta):
        if not self.rows:
            return
        new = max(0, min(len(self.rows) - 1, self.selected + delta))
        if new == self.selected:
            return
        self._select(new)
        row_top = self.HEADER_H + new * self.ROW_H
        row_bottom = row_top + self.ROW_H
        view_bottom = self.y_offset + self.table_canvas.winfo_height()
        if row_top < self.y_offset + self.HEADER_H:
            self.y_offset = max(0, row_top - self.HEADER_H)
        elif row_bottom > view_bottom:
            self.y_offset = min(self._max_y_offset(),
                                row_bottom - self.table_canvas.winfo_height())
        self._update_scrollbars()
        self._redraw_table()

    def _page_size(self):
        height = self.table_canvas.winfo_height() - self.HEADER_H
        return max(1, height // self.ROW_H)

    def _heat_color(self, t):
        """Interpolate a dark green -> orange -> red heatmap color."""
        stops = ((24, 90, 33), (190, 100, 0), (170, 25, 25))
        t = max(0.0, min(1.0, t))
        if t < 0.5:
            u = t * 2.0
            a, b = stops[0], stops[1]
        else:
            u = (t - 0.5) * 2.0
            a, b = stops[1], stops[2]
        rgb = tuple(int(round(a[i] + (b[i] - a[i]) * u)) for i in range(3))
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _cell_color(self, value, min_v, max_v, reverse=False):
        span = max_v - min_v
        t = 0.5 if span == 0 else (value - min_v) / span
        if reverse:
            t = 1.0 - t
        return self._heat_color(t)

    def _header_for(self, key):
        for header, k, _, _ in self.COLUMNS:
            if k == key:
                return header
        return key

    def _decimal_places(self, value):
        """Return the number of meaningful decimal places in a numeric value."""
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
        """Cache per-column scales and decimal places from the current rows."""
        self._decimals = {}
        self._scales = {}
        for key in self.numeric_keys:
            values = [row[key] for row in self.rows]
            if key in self.RATIO_KEYS or key in ("energy", "heat"):
                self._decimals[key] = 3
            else:
                self._decimals[key] = max(self._decimal_places(value)
                                          for value in values)
            self._scales[key] = (min(values), max(values)) if values else (0.0, 0.0)

    def _redraw_table(self):
        canvas = self.table_canvas
        canvas.delete("all")
        if not self.rows:
            return

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        # Each numeric column is scaled independently from green to red, and
        # formatted with enough decimal places to keep its values aligned.
        scales = self._scales
        decimals = self._decimals

        first = max(0, int(self.y_offset // self.ROW_H))
        last = min(len(self.rows),
                   int((self.y_offset + height - self.HEADER_H) // self.ROW_H) + 2)
        for index in range(first, last):
            y0 = self.HEADER_H + index * self.ROW_H - self.y_offset
            y1 = y0 + self.ROW_H
            selected = index == self.selected
            for key, x, col_w, anchor in self._col_layout:
                x0 = x - self.x_offset
                x1 = x + col_w - self.x_offset
                if x1 < 0 or x0 > width:
                    continue
                if key in scales:
                    color = self._cell_color(self.rows[index][key],
                                             *scales[key],
                                             reverse=(key in self.reversed_keys))
                    canvas.create_rectangle(x0, y0, x1 + 1, y1,
                                            fill=color, outline="")
                text_x = x1 - 6 if anchor == "e" else x0 + 6
                text_fill = "#ffffff" if selected else FG
                canvas.create_text(text_x, y0 + self.ROW_H // 2,
                                   anchor=anchor,
                                   text=self._format_cell(self.rows[index], key,
                                                          decimals.get(key, 0)),
                                   fill=text_fill)
            if selected:
                canvas.create_rectangle(1, y0 + 1, width - 1, y1 - 1,
                                        fill="", outline=SELECT_BG, width=2)

        # Header row is drawn last so scrolled cells never cover it.
        for key, x, col_w, anchor in self._col_layout:
            x0 = x - self.x_offset
            x1 = x + col_w - self.x_offset
            if x1 < 0 or x0 > width:
                continue
            canvas.create_rectangle(x0, 0, x1, self.HEADER_H,
                                    fill="#2d2d2d", outline="#111111")
            text_x = x1 - 6 if anchor == "e" else x0 + 6
            canvas.create_text(text_x, self.HEADER_H // 2,
                               anchor=anchor, text=self._header_for(key),
                               fill=FG)

    def _column_at(self, x):
        for key, col_x, col_w, _ in self._col_layout:
            if col_x <= x < col_x + col_w:
                return key
        return None

    def _on_click(self, event):
        if not self.rows:
            return
        if event.y < self.HEADER_H:
            key = self._column_at(event.x + self.x_offset)
            if key:
                self._on_sort(key)
            return
        row_index = int((event.y + self.y_offset - self.HEADER_H) // self.ROW_H)
        if 0 <= row_index < len(self.rows):
            self._select(row_index)

    def _on_wheel(self, event):
        if event.state & 0x0001:  # Shift held: scroll horizontally.
            self.x_offset -= (1 if event.delta > 0 else -1) * 40
        else:
            self.y_offset -= (1 if event.delta > 0 else -1) * self.ROW_H
        self._clamp_offsets()
        self._update_scrollbars()
        self._schedule_redraw()

    def _on_y_scrollbar(self, action, *args):
        content = self._content_height()
        if action == "moveto":
            self.y_offset = int(float(args[0]) * content)
        elif action == "scroll":
            amount = int(args[1])
            if args[2] == "units":
                self.y_offset += amount * self.ROW_H
            else:
                self.y_offset += amount * max(1, self.table_canvas.winfo_height())
        self._clamp_offsets()
        self._update_scrollbars()
        self._schedule_redraw()

    def _on_x_scrollbar(self, action, *args):
        content = self._content_width
        if action == "moveto":
            self.x_offset = int(float(args[0]) * content)
        elif action == "scroll":
            amount = int(args[1])
            if args[2] == "units":
                self.x_offset += amount * 40
            else:
                self.x_offset += amount * max(1, self.table_canvas.winfo_width())
        self._clamp_offsets()
        self._update_scrollbars()
        self._schedule_redraw()

    def _max_y_offset(self):
        return max(0, self.HEADER_H + len(self.rows) * self.ROW_H
                   - self.table_canvas.winfo_height())

    def _max_x_offset(self):
        return max(0, self._content_width - self.table_canvas.winfo_width())

    def _clamp_offsets(self):
        self.y_offset = max(0, min(self.y_offset, self._max_y_offset()))
        self.x_offset = max(0, min(self.x_offset, self._max_x_offset()))

    def _update_scrollbars(self):
        viewport_h = max(1, self.table_canvas.winfo_height())
        content_h = self._content_height()
        if content_h <= viewport_h:
            self.y_scroll.set(0.0, 1.0)
        else:
            first = self.y_offset / content_h
            last = (self.y_offset + viewport_h) / content_h
            self.y_scroll.set(first, min(1.0, last))

        viewport_w = max(1, self.table_canvas.winfo_width())
        content_w = self._content_width
        if content_w <= viewport_w:
            self.x_scroll.set(0.0, 1.0)
        else:
            first = self.x_offset / content_w
            last = (self.x_offset + viewport_w) / content_w
            self.x_scroll.set(first, min(1.0, last))

    def _content_height(self):
        return self.HEADER_H + len(self.rows) * self.ROW_H

    def _schedule_redraw(self):
        if not self._redraw_scheduled:
            self._redraw_scheduled = True
            self.table_canvas.after_idle(self._do_redraw)

    def _do_redraw(self):
        self._redraw_scheduled = False
        self._redraw_table()

    def _on_table_configure(self, event):
        if self._configure_after_id is not None:
            self.table_canvas.after_cancel(self._configure_after_id)
        self._configure_after_id = self.table_canvas.after(50,
                                                           self._do_configure_redraw)

    def _do_configure_redraw(self):
        self._configure_after_id = None
        self._clamp_offsets()
        self._update_scrollbars()
        self._redraw_table()

    def _on_right_click(self, event):
        if not self.rows or event.y < self.HEADER_H:
            return
        row_index = int((event.y + self.y_offset - self.HEADER_H) // self.ROW_H)
        if 0 <= row_index < len(self.rows):
            self._select(row_index)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def _copy_name(self):
        if self.selected < 0 or self.selected >= len(self.rows):
            return
        name = self.rows[self.selected]["name"]
        self.root.clipboard_clear()
        self.root.clipboard_append(name)
        self.root.update()

    def _show_preview(self, row):
        self._current_row = row
        self.name_var.set(self._preview_title(row))

        decimals = self._decimals
        lines = list(self._extra_preview_lines(row))
        for header, key, _, _ in self.COLUMNS:
            if key == "name":
                continue
            value = row.get(key, "")
            if isinstance(value, str):
                lines.append("{}: {}".format(header, value))
            else:
                lines.append("{}: {}".format(
                    header, self._format_cell(row, key, decimals.get(key, 0))))
        self.stats_var.set("\n".join(lines))
        self._redraw_preview()

    def _redraw_preview(self):
        canvas = self.canvas
        canvas.delete("all")
        if self._current_row is None:
            return

        path = self._row_image_path(self._current_row)
        if path is None:
            canvas.create_text(10, 10, anchor="nw", text="No image.", fill=FG)
            return

        photo = self._load_photo(path, self.preview_size)
        if photo is None:
            canvas.create_text(10, 10, anchor="nw", text="No image.", fill=FG)
            return

        self._current_photo = photo
        canvas.create_image(canvas.winfo_width() // 2,
                            canvas.winfo_height() // 2,
                            image=photo, anchor="center")

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

    def _base_rows(self):
        """Return the rows to display before filtering and sorting."""
        return self.all_rows

    def _build_extra_bar(self, bar):
        """Hook for subclasses to add extra top-bar controls."""

    def _build_context_menu(self, menu):
        menu.add_command(label="Copy Name",
                         command=self._copy_name)

    def _preview_title(self, row):
        return row["name"]

    def _extra_preview_lines(self, row):
        return []

    def _load_photo(self, path, max_size):
        if path in self._photo_cache:
            return self._photo_cache[path]
        try:
            image = tk.PhotoImage(file=path)
        except tk.TclError:
            return None
        largest = max(image.width(), image.height())
        if largest > max_size:
            factor = (largest + max_size - 1) // max_size
            image = image.subsample(factor, factor)
        self._photo_cache[path] = image
        return image

    def _start_preload(self):
        """Queue every outfit thumbnail for loading once, in the background."""
        paths = []
        seen = set()
        for row in self.rows:
            path = self._row_image_path(row)
            if path and path not in seen:
                seen.add(path)
                paths.append(path)
        self._preload_paths = paths
        self._preload_index = 0
        self._preload_attempted = set()
        self._update_preload_status()
        if paths:
            self.root.after(16, self._preload_next)

    def _preload_next(self):
        """Load one uncached thumbnail per tick, yielding to the event loop."""
        while self._preload_index < len(self._preload_paths):
            path = self._preload_paths[self._preload_index]
            self._preload_index += 1
            if path in self._photo_cache or path in self._preload_attempted:
                continue
            self._preload_attempted.add(path)
            self._load_photo(path, self.preview_size)
            self._update_preload_status()
            break
        if self._preload_index < len(self._preload_paths):
            self.root.after(16, self._preload_next)
        else:
            self._update_preload_status()

    def _update_preload_status(self):
        total = len(self.rows)
        noun = self.NOUN
        if total == 0:
            self.status_var.set("No {}s.".format(noun))
            return
        loaded = 0
        for row in self.rows:
            path = self._row_image_path(row)
            if path is None or path in self._photo_cache:
                loaded += 1
        self.status_var.set("{} / {} {}s loaded".format(loaded, total, noun))


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
            self.root.after(0, self._on_data_loaded, ships, full_rows, deduped)
        except Exception as exc:  # pragma: no cover - surfaced in the UI.
            self.root.after(0, self._load_error, str(exc))

    def _on_data_loaded(self, ships, full_rows, deduped_rows):
        self.ships = ships
        self.full_rows = full_rows
        self.deduped_rows = deduped_rows
        self._refresh_rows()

    def _base_rows(self):
        if self.show_all_var is None:
            return self.deduped_rows
        return self.full_rows if self.show_all_var.get() else self.deduped_rows

    def _build_extra_bar(self, bar):
        self.show_all_var = tk.BooleanVar(
            value=bool(self.config.get("show_all", False)))
        ttk.Checkbutton(bar, text="Show all variants",
                        variable=self.show_all_var,
                        command=self._on_show_all).pack(side=tk.RIGHT, padx=8)

    def _on_show_all(self):
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
                # Animated ships store frames either in a directory named
                # after the sprite (e.g. "ship/avgi koryfi/koryfi" ->
                # koryfi-00.png) or beside it (e.g. "ship/hallucination" ->
                # hallucination-0.png).
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
        menu.add_command(label="Copy Source Name",
                         command=lambda: self._copy_field("name"))
        menu.add_command(label="Copy In-Game Name",
                         command=lambda: self._copy_field("display_name"))
        menu.add_separator()
        menu.add_command(label="Copy Both Names",
                         command=self._copy_both_names)

    def _copy_field(self, key):
        if self.selected < 0 or self.selected >= len(self.rows):
            return
        self._copy_to_clipboard(str(self.rows[self.selected][key]))

    def _copy_both_names(self):
        if self.selected < 0 or self.selected >= len(self.rows):
            return
        row = self.rows[self.selected]
        self._copy_to_clipboard("{}\t{}".format(row["name"], row["display_name"]))

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

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


if __name__ == "__main__":
    main()
