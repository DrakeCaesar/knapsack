"""Locating game sprites, including high-DPI plugin art."""

import os

from .paths import PLUGINS_DIR


def find_plugin_images_dir():
    """Locate the images folder of the first plugin that ships game images."""
    if not os.path.isdir(PLUGINS_DIR):
        return None
    for name in sorted(os.listdir(PLUGINS_DIR)):
        images = os.path.normpath(os.path.join(PLUGINS_DIR, name, "images"))
        if os.path.isdir(images):
            return images
    return None
