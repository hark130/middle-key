"""Define macro constants as a single point of truth."""

# Standard Imports
from typing import Final
# Third Party Imports
# Local Imports

DC_BLOCK_POLE: Final[float] = 0.995  # DC blocker pole: cutoff = (1 - pole) * fs / (2 * pi)
# Assumed file extensions
SIGMF_DATA_FILE_EXT: Final[str] = 'sigmf-data'
SIGMF_META_FILE_EXT: Final[str] = 'sigmf-meta'
