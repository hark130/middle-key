"""Demodulation."""

# Standard Imports
# Third Party Imports
import numpy as np
# Local Imports


def demod_am(samples: np.ndarray) -> np.ndarray:
    """Detect the envelope of complex baseband AM samples: |I + jQ|.

    Args:
        samples: Complex baseband samples.

    Returns:
        The envelope: one real value per sample.
    """
    # LOCAL VARIABLES
    envelope = None  # |I + jQ|

    # DEMOD IT
    envelope = np.abs(samples)

    # DONE
    return envelope
