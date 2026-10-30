"""Demodulation."""

# Standard Imports
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.constants import NORMALIZE_PERCENTILE, NORMALIZE_TARGET
from middle_key.dsp import filter_audio, normalize_audio, remove_dc


def detect_envelope(samples: np.ndarray) -> np.ndarray:
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


def extract_audio(samples: np.ndarray, sample_rate: float) -> np.ndarray:
    """Demodulate complex baseband AM samples into voice audio.

    Runs the AM receive chain: detect the envelope (|I + jQ|), remove the carrier's DC level,
    then low-pass filter the result to the voice band.  The audio keeps its true level, which
    reflects the signal strength; see normalize_audio() to scale it for playback or a file.

    Args:
        samples: Complex baseband samples, centered on the AM carrier.
        sample_rate: The sample rate in samples per second.

    Returns:
        Real audio samples at sample_rate, one per input sample.

    Raises:
        IndexError: samples is empty.
        ValueError: sample_rate is too low for the voice-band filter (see design_lowpass()).
    """
    raw_demod = detect_envelope(samples)
    dc_free = remove_dc(raw_demod)
    filtered = filter_audio(audio=dc_free, sample_rate=sample_rate)
    return filtered


def extract_normal_audio(samples: np.ndarray, sample_rate: float,
                         percentile: float = NORMALIZE_PERCENTILE,
                         target: float = NORMALIZE_TARGET) -> np.ndarray:
    """Demodulate complex baseband AM samples into voice audio, normalized for playback.

    A convenience wrapper: extract_audio() followed by normalize_audio().  Normalization applies
    one gain to all of samples, so if samples holds several transmissions, quiet ones stay
    quieter than loud ones.

    Args:
        samples: Complex baseband samples, centered on the AM carrier.
        sample_rate: The sample rate in samples per second.
        percentile: [OPTIONAL] The percentile (0-100) of |audio| to scale to target.
        target: [OPTIONAL] The level, between 0 and 1, the percentile is scaled to.

    Returns:
        Real audio samples at sample_rate, one per input sample, within +/-1.

    Raises:
        IndexError: samples is empty.
        ValueError: sample_rate is too low for the voice-band filter, percentile or target is
            out of range, or the audio contains NaN or infinite values.
    """
    audio = extract_audio(samples=samples, sample_rate=sample_rate)
    normal = normalize_audio(audio=audio, percentile=percentile, target=target)
    return normal
