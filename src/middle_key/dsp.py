"""Digital signal processing helpers."""

# Standard Imports
# Third Party Imports
import numpy as np
# Local Imports


def power_db(samples: np.ndarray) -> np.ndarray:
    """Convert samples to instantaneous power in dB relative to full scale (dBFS).

    A sample with a magnitude of 1.0 is 0 dBFS.  This is the same scale GNU Radio's Power Squelch
    uses for its threshold, so the two can be compared directly.

    Args:
        samples: Real or complex samples.

    Returns:
        An array of power values in dBFS, one per sample.
    """
    # LOCAL VARIABLES
    power_dbfs = power_to_db(np.abs(samples).astype(np.float64)**2)  # Return value: |x|^2 in dB

    # DONE
    return power_dbfs


def power_to_db(power: np.ndarray) -> np.ndarray:
    """Convert power values (not amplitudes) to dB: 10 * log10(power).

    Values of zero are clamped to the smallest positive float so the result is finite.

    Args:
        power: Power values, e.g., |x|^2 or a power spectral density.

    Returns:
        An array of the same shape, in dB.
    """
    # LOCAL VARIABLES
    floor = np.finfo(np.float64).tiny  # Smallest positive power: avoids log10(0) = -inf
    power_dbs = None                   # Return value

    # CONVERT IT
    power_dbs = 10.0 * np.log10(np.maximum(power, floor))

    # DONE
    return power_dbs
