#!/usr/bin/env python3
"""Entry point for the Endless Sky data tools GUI.

Run from the repository root (or anywhere) with:

    python knapsack/endless_sky_tools.py

The window has five tabs:

  * "Engine Picker" - lists every non-dominated (thrust, turn) combination,
    each with two small bars: blue for forward thrust and orange for turning.
    Click a row to see the exact engine list on the right.

  * "Ship Bunks" - lists every ship by its maximum achievable crew capacity,
    showing the ship sprite next to the table.

  * "Generators" - compares the stats of every generator outfit, showing the
    outfit thumbnail next to the table.

  * "Engines" - compares the stats of every engine outfit.

  * "Weapons" - compares weapon stats, with a sub-tab per weapon type.
"""

import os
import sys

KNAPSACK_DIR = os.path.dirname(os.path.abspath(__file__))
if KNAPSACK_DIR not in sys.path:
    sys.path.insert(0, KNAPSACK_DIR)

from es_tools import main  # noqa: E402

if __name__ == "__main__":
    main()
