"""The reusable heatmap table: a virtualized canvas table for comparing
outfit stats with per-column green-to-red coloring and auto-sized widths.
"""

import json
import os
import threading
import tkinter as tk
from tkinter import ttk

import engine_knapsack as ek

from .images import find_plugin_images_dir
from .paths import DATA_DIR, IMAGES_DIR
from .theme import BG, FG, ENTRY_BG, SELECT_BG


class OutfitTableApp(ttk.Frame):
    """Reusable heatmap table for comparing outfit stats."""

    COLUMNS = []
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
    HEADER_H = 26
    # Extra total horizontal padding added when auto-sizing column widths; it
    # is split evenly on either side of the widest cell text. The same amount
    # is used to inset the text when drawing it, so the text fills the cell.
    CELL_PADDING = 16

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
        self.numeric_keys = [key for _, key, _ in self.COLUMNS
                             if key not in self.TEXT_KEYS]
        self.reversed_keys = self.REVERSED_KEYS
        self.selected = -1
        self.y_offset = 0
        self.x_offset = 0
        self._col_layout = []
        self._content_width = 0
        self._scales = {}
        self._decimals = {}
        # Hidden canvas used to measure the exact rendered text width. A plain
        # tkfont.Font() does not match the canvas default font, which made the
        # auto-sized columns wider than the text they contain.
        self._measure_canvas = tk.Canvas(self, width=1, height=1,
                                         highlightthickness=0)
        self._measure_cache = {}
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

        # Column widths are derived from content (widest text, header
        # included). Size the columns now so the table is drawable before the
        # data finishes loading; _refresh_rows() re-sizes them from real rows.
        self._compute_column_widths()

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
        self._compute_column_widths()
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
        for header, k, _ in self.COLUMNS:
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
            if not values:
                continue
            if key in self.RATIO_KEYS or key in self.THREE_DECIMAL_KEYS:
                self._decimals[key] = 3
            else:
                self._decimals[key] = max(self._decimal_places(value)
                                          for value in values)
            self._scales[key] = (min(values), max(values))

    def _visible_columns(self):
        """Return the columns to display for the current rows.

        When HIDE_ZERO_COLUMNS is set, numeric columns that are all zero for
        every row are dropped (e.g. a damage type no weapon of this group
        deals).
        """
        if not self.HIDE_ZERO_COLUMNS:
            return self.COLUMNS
        hidden = set()
        for key in self.numeric_keys:
            values = [row[key] for row in self.rows]
            if values and all(value == 0 for value in values):
                hidden.add(key)
        return [column for column in self.COLUMNS if column[1] not in hidden]

    def _compute_column_widths(self):
        """Auto-size every column to its widest text.

        Widths are derived purely from content: the exact rendered width of the
        longest formatted cell in each column, including the header text, so no
        width is ever declared. The total content width is the sum of all
        column widths.
        """
        decimals = self._decimals

        x = 0
        layout = []
        for header, key, anchor in self._visible_columns():
            longest = self._measure_text(header)
            for row in self.rows:
                text = self._format_cell(row, key, decimals.get(key, 0))
                longest = max(longest, self._measure_text(text))
            # Same padding on both sides of the text; CELL_PADDING is the total
            # added to the width, split evenly when the text is drawn.
            width = longest + self.CELL_PADDING
            layout.append((key, x, width, anchor))
            x += width
        self._col_layout = layout
        self._content_width = x

    def _measure_text(self, text):
        """Return the exact rendered pixel width of ``text``.

        Uses a hidden canvas with the same default font as the table, so the
        width matches what is actually drawn (font.measure() does not).
        """
        width = self._measure_cache.get(text)
        if width is not None:
            return width
        canvas = self._measure_canvas
        item = canvas.create_text(0, 0, anchor="nw", text=text)
        x1, _, x2, _ = canvas.bbox(item)
        canvas.delete(item)
        width = x2 - x1
        self._measure_cache[text] = width
        return width

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

        # Half the column padding goes on each side of the text, matching the
        # width calculation so the text fills the cell exactly.
        inset = self.CELL_PADDING / 2.0

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
                text_x = x1 - inset if anchor == "e" else x0 + inset
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
            text_x = x1 - inset if anchor == "e" else x0 + inset
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
        for header, key, _ in self._visible_columns():
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
