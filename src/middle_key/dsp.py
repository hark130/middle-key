"""Digital signal processing helpers."""

# Standard Imports
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.constants import DC_BLOCK_POLE


def convert_samples_to_db(samples: np.ndarray) -> np.ndarray:
    """Convert samples to instantaneous power in dB relative to full scale (dBFS).

    A sample with a magnitude of 1.0 is 0 dBFS.  This is the same scale GNU Radio's Power Squelch
    uses for its threshold, so the two can be compared directly.

    Args:
        samples: Real or complex samples.

    Returns:
        An array of power values in dBFS, one per sample.
    """
    # LOCAL VARIABLES
    power_dbfs = convert_power_to_db(np.abs(samples).astype(np.float64)**2)  # |x|^2 in dB

    # DONE
    return power_dbfs


def convert_power_to_db(power: np.ndarray) -> np.ndarray:
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


def remove_dc(signal_in: np.ndarray, pole: float = DC_BLOCK_POLE) -> np.ndarray:
    """Remove the DC level with a one-pole high-pass filter: y[n] = x[n] - x[n-1] + pole*y[n-1].

    The filter starts "primed" with the first sample's level, as if the input had always been at
    that level, so the start of the output doesn't jump from zero to the full carrier level.

    Args:
        signal_in: Real samples, e.g., an AM envelope.
        pole: Between 0 and 1.  Closer to 1 lowers the cutoff, (1 - pole) * fs / (2 * pi), but
            takes longer, 1 / (1 - pole) samples, to settle after the DC level changes.

    Returns:
        The input with its DC level removed.
    """
    # LOCAL VARIABLES
    b_coeffs = np.array([1.0, -1.0])   # Feed-forward coefficients: x[n] - x[n-1]
    a_coeffs = np.array([1.0, -pole])  # Feedback coefficients: y[n] - pole * y[n-1]
    init_state = None                  # Filter state matching a steady input at signal_in[0]
    blocked = None                     # Return value

    # FILTER IT
    init_state = signal.lfilter_zi(b_coeffs, a_coeffs) * signal_in[0]
    blocked, _ = signal.lfilter(b_coeffs, a_coeffs, signal_in, zi=init_state)

    # DONE
    return blocked
