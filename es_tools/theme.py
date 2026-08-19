"""Dark theme: shared colors and ttk styling for the whole app."""

import tkinter as tk
from tkinter import ttk

# Dark theme colors shared by all tabs.
BG = "#1e1e1e"
FG = "#e0e0e0"
ENTRY_BG = "#2d2d2d"
SELECT_BG = "#264f78"


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
