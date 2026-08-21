"""The Systems tab: comparison tables grouped by system series.

Each system series (Shields, Cooling, Scanners, Repair, ...) gets its own
tab so the stats are comparable within each group.
"""

from .outfits import SYSTEMS_COLUMNS, build_systems_rows, system_series
from .series import SeriesApp, SeriesTable


class SystemCategoryTable(SeriesTable):
    """Heatmap table comparing the systems of a single series."""

    COLUMNS = SYSTEMS_COLUMNS
    BUILDER = build_systems_rows
    TEXT_KEYS = {"name", "faction", "series"}
    REVERSED_KEYS = {"shields", "shield_generation", "cooling", "scan_power",
                     "hull_repair", "hull", "jamming", "fuel_capacity",
                     "ramscoop"}
    RATIO_KEYS = set()
    NOUN = "system"
    DEFAULT_SORT_KEY = "name"
    CONFIG_FILENAME = ".endless_sky_systems.json"


class SystemsApp(SeriesApp):
    """Tab comparing systems, split into one tab per system series."""

    TABLE_CLS = SystemCategoryTable
    SERIES_FN = system_series
    LABEL = "Loading systems..."
