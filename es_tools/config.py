"""App-wide configuration for how game data is processed."""

# Exclude outfits whose cost is 0. These are special / NPC-only items that
# don't appear in normal gameplay (or are used for something else entirely),
# so they would just clutter the comparison tables.
EXCLUDE_ZERO_COST = True

# Eagerly load every thumbnail into memory at startup. When False, thumbnails
# are loaded lazily as rows are selected instead.
PRELOAD_IMAGES = False
