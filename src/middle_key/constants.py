"""Define macro constants as a single point of truth."""

# Standard Imports
from typing import Final
# Third Party Imports
# Local Imports

# Audio low-pass filter
AUDIO_CUTOFF_HZ: Final[float] = 3_000.0      # Airband voice is roughly 300-3000 Hz
AUDIO_TRANSITION_HZ: Final[float] = 1_000.0  # Passband edge to stopband edge
# DC blocker
DC_BLOCK_POLE: Final[float] = 0.995  # DC blocker pole: cutoff = (1 - pole) * fs / (2 * pi)
# FIR filter design
HAMMING_TAPS_FACTOR: Final[float] = 3.3  # Hamming window: num taps ~= factor * fs / transition
# Assumed file extensions
SIGMF_DATA_FILE_EXT: Final[str] = 'sigmf-data'
SIGMF_META_FILE_EXT: Final[str] = 'sigmf-meta'
