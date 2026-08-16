#!/usr/bin/env python3
"""A small tkinter GUI for the engine knapsack solver.

Run from the repository root (or anywhere) with:

    python knapsack/engine_knapsack_gui.py

The left panel lists every non-dominated (thrust, turn) combination, each with
two small bars: blue for forward thrust and orange for turning. Click a row to
see the exact engine list on the right.
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


class EnginePickerApp:
    ROW_H = 30
    ENGINE_ROW_H = 168
    THRUST_COLOR = "#4a90d9"
    TURN_COLOR = "#e08a4a"

    def __init__(self, root):
        self.root = root
        root.title("Endless Sky Engine Picker")
        root.geometry("900x560")

        self.config_path = os.path.join(os.path.expanduser("~"),
                                        ".endless_sky_engine_picker.json")
        self._save_after_id = None
        self._load_config()

        self.data_dir = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
        self.outfits = None
        self.engines = []
        self.capacity = 0
        self.results = []
        self.selected = -1
        self.scroll = 0

        self.images_dir = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "images"))
        self._photo_cache = {}
        self.engine_entries = []
        self.engine_scroll = 0

        self.factions = []
        self.faction_vars = {}
        self._debounce_id = None
        self._computing = False
        self._pending = False

        self.bg = "#1e1e1e"
        self.fg = "#e0e0e0"
        self.entry_bg = "#2d2d2d"
        self.select_bg = "#264f78"
        self.mono_font = (self._find_fira_code_family(), 9)

        self._apply_theme()
        self._build_controls()
        self._build_faction_bar()
        self._build_panels()

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        root.bind("<Configure>", self._on_configure)
        root.bind("<Up>", self._on_up)
        root.bind("<Down>", self._on_down)

        self._start_loading()

    def _find_fira_code_family(self):
        """Return the installed Fira Code Nerd Font family name, if present."""
        families = set(tkfont.families(self.root))
        for candidate in ("FiraCode Nerd Font", "Fira Code Nerd Font",
                          "FiraCode Nerd Font Mono", "Fira Code Nerd Font Mono"):
            if candidate in families:
                return candidate
        for name in sorted(families):
            lower = name.lower()
            if "fira" in lower and "nerd" in lower:
                return name
        return "Fira Code"

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

    # --------------------------------------------------------------- theme
    def _apply_theme(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # The root window shows through the spacing around the paned window, so
        # it must be dark as well, or thin white strips appear at the edges.
        self.root.configure(bg=self.bg)

        style.configure(".", background=self.bg, foreground=self.fg,
                        fieldbackground=self.entry_bg)
        style.configure("TFrame", background=self.bg)
        style.configure("TLabel", background=self.bg, foreground=self.fg)
        style.configure("TButton", background="#333333", foreground=self.fg,
                        borderwidth=1, focusthickness=1, focuscolor=self.bg)
        style.map("TButton",
                  background=[("active", "#3c3c3c"), ("pressed", "#2a2a2a")])
        style.configure("TEntry", fieldbackground=self.entry_bg,
                        foreground=self.fg, insertcolor=self.fg)
        style.configure("TCheckbutton", background=self.bg, foreground=self.fg)
        style.map("TCheckbutton",
                  background=[("active", self.bg)],
                  foreground=[("active", self.fg)])
        style.configure("TPanedwindow", background=self.bg)
        style.configure("Treeview", background=self.entry_bg,
                        fieldbackground=self.entry_bg, foreground=self.fg,
                        borderwidth=0, rowheight=24)
        style.configure("Treeview.Heading", background="#2d2d2d",
                        foreground=self.fg, borderwidth=0)
        style.map("Treeview",
                  background=[("selected", self.select_bg)],
                  foreground=[("selected", "#ffffff")])
        style.configure("TScrollbar", background="#3a3a3a",
                        troughcolor="#2d2d2d", bordercolor="#2d2d2d",
                        arrowcolor=self.fg)
        style.map("TScrollbar", background=[("active", "#4a4a4a")])

    # ------------------------------------------------------------------ UI
    def _build_controls(self):
        bar = ttk.Frame(self.root, padding=8)
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
        self.checkbox_frame = ttk.Frame(self.root, padding=(8, 0, 8, 4))
        self.checkbox_frame.pack(side=tk.TOP, fill=tk.X)

    def _build_panels(self):
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
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
            self.engine_entries = []
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

        entries = []
        for count, engine in counts.values():
            entries.append((count, engine, self._thumbnail(engine)))
        entries.sort(key=lambda entry: -entry[1]["weight"])

        self.engine_entries = entries
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
        if not self.engine_entries:
            canvas.create_text(10, 10, anchor="nw", text="Select a result.",
                               fill=self.fg)
            return

        y = 4 - self.engine_scroll
        for count, engine, photo in self.engine_entries:
            if y + self.ENGINE_ROW_H < 0:
                y += self.ENGINE_ROW_H
                continue
            if y > canvas.winfo_height():
                break

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

            y += self.ENGINE_ROW_H

    def _on_engine_wheel(self, event):
        if not self.engine_entries:
            return
        step = -1 if event.delta > 0 else 1
        self.engine_scroll += step * self.ENGINE_ROW_H
        self._clamp_engine_scroll()
        self.redraw_engines()
        self._update_engine_scrollbar()

    def _on_engine_scrollbar(self, action, *args):
        if not self.engine_entries:
            return
        total = self._max_engine_scroll()
        if action == "moveto":
            self.engine_scroll = int(float(args[0]) * total)
        elif action == "scroll":
            amount = int(args[1])
            if args[2] == "units":
                self.engine_scroll += amount * self.ENGINE_ROW_H
            else:
                self.engine_scroll += amount * max(1, self.engine_canvas.winfo_height())
        self._clamp_engine_scroll()
        self.redraw_engines()
        self._update_engine_scrollbar()

    def _max_engine_scroll(self):
        visible = self.engine_canvas.winfo_height()
        content = len(self.engine_entries) * self.ENGINE_ROW_H
        return max(0, content - visible)

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


def main():
    root = tk.Tk()
    EnginePickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
