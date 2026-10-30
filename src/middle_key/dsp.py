"""Digital signal processing helpers."""

# Standard Imports
import math
# Third Party Imports
from scipy import signal
import numpy as np
# Local Imports
from middle_key.constants import (AUDIO_CUTOFF_HZ, AUDIO_TRANSITION_HZ, DC_BLOCK_POLE,
                                  HAMMING_TAPS_FACTOR, NORMALIZE_PERCENTILE,
                                  NORMALIZE_TARGET)
from middle_key.demod import demod_am


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


def design_lowpass(sample_rate: float, cutoff_hz: float, transition_hz: float) -> np.ndarray:
    """Design a Hamming-windowed low-pass FIR filter.

    The passband ends at cutoff_hz and the stopband starts at cutoff_hz + transition_hz.  The
    number of taps comes from the Hamming window's rule of thumb, HAMMING_TAPS_FACTOR * fs /
    transition_hz, rounded up to an odd number so the filter delays every frequency by exactly
    (num_taps - 1) / 2 samples.

    Args:
        sample_rate: The sample rate, in samples per second, the filter will run at.
        cutoff_hz: The passband edge, in Hz.
        transition_hz: The width, in Hz, of the transition from passband to stopband.

    Returns:
        The filter taps (coefficients).

    Raises:
        ValueError: A non-positive value, or a stopband edge at or above the Nyquist frequency.
    """
    # LOCAL VARIABLES
    half_taps = 0  # Half the rule-of-thumb tap count, rounded up
    taps = None    # Return value

    # INPUT VALIDATION
    if sample_rate <= 0 or cutoff_hz <= 0 or transition_hz <= 0:
        raise ValueError(f'All arguments must be positive: sample_rate={sample_rate}, '
                         f'cutoff_hz={cutoff_hz}, transition_hz={transition_hz}')
    if cutoff_hz + transition_hz >= sample_rate / 2:
        raise ValueError(f'The stopband edge ({cutoff_hz + transition_hz} Hz) must be below the '
                         f'Nyquist frequency ({sample_rate / 2} Hz)')

    # DESIGN IT
    half_taps = math.ceil(HAMMING_TAPS_FACTOR * sample_rate / transition_hz / 2)
    # firwin's cutoff is the -6 dB point, in the middle of the transition band
    taps = signal.firwin(2 * half_taps + 1, cutoff_hz + transition_hz / 2, window='hamming',
                         fs=sample_rate)

    # DONE
    return taps


def extract_audio(samples: np.ndarray, sample_rate: float) -> np.ndarray:
    """Demodulate analog AM, remove the DC, and filter the voice."""
    raw_demod = demod_am(samples)
    dc_free = remove_dc(raw_demod)
    filtered = filter_audio(audio=dc_free, sample_rate=sample_rate)
    return filtered


def extract_normal_audio(samples: np.ndarray, sample_rate: float,
                         percentile: float = NORMALIZE_PERCENTILE,
                         target: float = NORMALIZE_TARGET) -> np.ndarray:
    """Extract normalized audio from the samples."""
    audio = extract_audio(samples=samples, sample_rate=sample_rate)
    normal = normalize_audio(audio=audio, percentile=percentile, target=target)
    return normal


def filter_audio(audio: np.ndarray, sample_rate: float, cutoff_hz: float = AUDIO_CUTOFF_HZ,
                 transition_hz: float = AUDIO_TRANSITION_HZ) -> np.ndarray:
    """Low-pass filter audio to the voice band, removing hiss above it.

    The output is delayed by (num_taps - 1) / 2 samples, about 1.7 ms with the defaults at
    48 kS/s, and starts with a short ramp-up while the filter fills with samples.

    Args:
        audio: Real audio samples, e.g., a demodulated AM envelope with its DC level removed.
        sample_rate: The audio sample rate in samples per second.
        cutoff_hz: [OPTIONAL] The passband edge, in Hz.
        transition_hz: [OPTIONAL] The width, in Hz, of the transition from passband to stopband.

    Returns:
        The filtered audio, the same length as the input.

    Raises:
        ValueError: Bad filter parameters (see design_lowpass()).
    """
    # LOCAL VARIABLES
    taps = design_lowpass(sample_rate, cutoff_hz, transition_hz)  # Filter coefficients
    filtered = None                                               # Return value

    # FILTER IT
    filtered = signal.lfilter(taps, 1.0, audio)

    # DONE
    return filtered


def normalize_audio(audio: np.ndarray, percentile: float = NORMALIZE_PERCENTILE,
                    target: float = NORMALIZE_TARGET) -> np.ndarray:
    """Scale audio by one constant gain so its loud parts land near target, then clip to +/-1.

    The level is measured at a high percentile of |audio| instead of its peak, so a few loud
    outliers (clicks, start-up transients) can't set the volume for everything else.  Samples
    above that percentile end up above target and may be clipped at +/-1.  Relative levels are
    unchanged: a quiet transmission stays quieter than a loud one.

    Args:
        audio: Real audio samples.
        percentile: [OPTIONAL] The percentile (0-100) of |audio| to scale to target.
        target: [OPTIONAL] The level, between 0 and 1, the percentile is scaled to.

    Returns:
        The scaled audio, within +/-1.  Empty or silent (all-zero) audio is returned unscaled.

    Raises:
        ValueError: percentile is outside 0-100 or target is outside (0, 1].
    """
    # LOCAL VARIABLES
    level = 0.0         # Magnitude of audio at the given percentile
    normalized = audio  # Return value

    # INPUT VALIDATION
    if not 0 <= percentile <= 100:
        raise ValueError(f'The percentile must be between 0 and 100, not {percentile}')
    if not 0 < target <= 1:
        raise ValueError(f'The target must be greater than 0 and at most 1, not {target}')
    if not np.all(np.isfinite(audio)):
        raise ValueError('The "audio" argument contains NaN or infinite values')

    # NORMALIZE IT
    if audio.size > 0:
        level = float(np.percentile(np.abs(audio), percentile))
    if level > 0:
        normalized = np.clip(audio * (target / level), -1.0, 1.0)

    # DONE
    return normalized


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
