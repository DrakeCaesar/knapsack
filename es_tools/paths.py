"""Path constants for the Endless Sky data tools.

The repo layout is::

    <repo>/
        data/
        images/
        plugins/
        knapsack/
            engine_knapsack.py       (data solver, unchanged dependency)
            endless_sky_tools.py     (entry script)
            es_tools/                (this package)
"""

import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
KNAPSACK_DIR = os.path.dirname(PACKAGE_DIR)
REPO_DIR = os.path.dirname(KNAPSACK_DIR)

DATA_DIR = os.path.join(REPO_DIR, "data")
IMAGES_DIR = os.path.join(REPO_DIR, "images")
PLUGINS_DIR = os.path.join(REPO_DIR, "plugins")
ICONS_DIR = os.path.join(REPO_DIR, "icons")
