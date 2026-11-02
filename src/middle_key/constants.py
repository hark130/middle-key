"""Define macro constants as a single point of truth."""

# Standard Imports
from typing import Final
import os
# Third Party Imports
# Local Imports

# Audio low-pass filter
AUDIO_CUTOFF_HZ: Final[float] = 3_000.0      # Airband voice is roughly 300-3000 Hz
AUDIO_TRANSITION_HZ: Final[float] = 1_000.0  # Passband edge to stopband edge
# CLI arguments
CLI_DEBUG: Final[str] = "debug"            # Debug mode
CLI_DEBUG_DEFAULT: Final[bool] = False     # Default debug mode
CLI_FREQ: Final[str] = "freq"              # Channel frequency in Hz
CLI_GAIN: Final[str] = "gain"              # RF gain in dB
CLI_GAIN_DEFAULT: Final[float] = 40.0      # Default gain value
CLI_OUT: Final[str] = "out"                # Directory to save output wav files
CLI_OUT_DEFAULT: Final[str] = os.getcwd()  # Default output to the current working directory
# DC blocker
DC_BLOCK_POLE: Final[float] = 0.995  # DC blocker pole: cutoff = (1 - pole) * fs / (2 * pi)
# Exit codes
EXIT_SUCCESS: Final[int] = 0  # Exit code for success
EXIT_FAILURE: Final[int] = 1  # Exit code for failure
# Audio normalization
NORMALIZE_PERCENTILE: Final[float] = 99.9  # Scale by this percentile of |audio|, not its peak
NORMALIZE_TARGET: Final[float] = 0.8       # Where that percentile lands: ~-2 dBFS of headroom
# FIR filter design
HAMMING_TAPS_FACTOR: Final[float] = 3.3  # Hamming window: num taps ~= factor * fs / transition
# Assumed file extensions
SIGMF_DATA_FILE_EXT: Final[str] = "sigmf-data"
SIGMF_META_FILE_EXT: Final[str] = "sigmf-meta"
