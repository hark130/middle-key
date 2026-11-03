"""Define macro constants as a single point of truth."""

# Standard Imports
from typing import Final
import os
# Third Party Imports
# Local Imports

# Audio low-pass filter
AUDIO_CUTOFF_HZ: Final[float] = 3_000.0      # Airband voice is roughly 300-3000 Hz
AUDIO_TRANSITION_HZ: Final[float] = 1_000.0  # Passband edge to stopband edge
# Burst detection (squelch) and recording
BURST_CLOSE_DB: Final[float] = 6.0           # End a burst when power drops below floor + this
BURST_CONFIRM_S: Final[float] = 0.25         # Power must stay up this long to count as a burst
BURST_FLOOR_PERCENTILE: Final[float] = 20.0  # Noise floor = this percentile of recent frame powers
BURST_FLOOR_WINDOW_S: Final[float] = 30.0    # Seconds of frame powers the noise floor looks at
BURST_FRAME_S: Final[float] = 0.010          # Measure power over frames this long: 10 ms
BURST_HANG_S: Final[float] = 0.3             # Hang time: stay open through dips shorter than this
BURST_OPEN_DB: Final[float] = 10.0           # Start a burst when power is this far above the floor
BURST_PAD_S: Final[float] = 0.15             # Keep this much extra audio before and after a burst
BURST_WARMUP_S: Final[float] = 2.0           # Measure the noise floor this long before detecting
# Channelizer
CHANNEL_CUTOFF_HZ: Final[float] = 5_000.0       # Voice (~3 kHz) plus margin for frequency error
CHANNEL_TARGET_RATE: Final[float] = 48_000.0    # Aim for this channel sample rate, S/s
CHANNEL_TRANSITION_HZ: Final[float] = 10_000.0  # Stopband edge at 15 kHz, under 48 kS/s / 2
# CLI arguments
CLI_DEBUG: Final[str] = "debug"            # Debug mode
CLI_FREQ: Final[str] = "freq"              # Channel frequency in Hz
CLI_GAIN: Final[str] = "gain"              # RF gain in dB
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
