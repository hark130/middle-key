"""Defines the Channelizer class: select one channel from a stream of wideband IQ chunks.

USAGE:
    from middle_key.channelizer import Channelizer

    channelizer = Channelizer(sample_rate=240e3, offset_hz=50e3)
    for chunk in sdr.stream_samples():
        channel = channelizer.process_chunk(chunk)  # at channelizer.channel_rate S/s
"""

# Standard Imports
import math
# Third Party Imports
from scipy import signal
import numpy as np
# Local Imports
from middle_key.constants import (CHANNEL_CUTOFF_HZ, CHANNEL_TARGET_RATE,
                                  CHANNEL_TRANSITION_HZ)
from middle_key.dsp import design_lowpass


class Channelizer:  # pylint: disable=too-many-instance-attributes
    """Select one channel from wideband IQ: mix it to 0 Hz, low-pass filter it, then decimate.

    Built for streaming: the mixer's phase, the filter's history, and the decimator's position
    carry over from one process_chunk() call to the next, so feeding a stream in chunks of any
    size gives the same output as feeding it all at once.  Create one Channelizer per channel.

    Attributes:
        offset_hz: The channel's frequency relative to the wideband stream's center, in Hz.
        decimation: Keep 1 of every decimation filtered samples.
        channel_rate: The output sample rate in samples per second (sample_rate / decimation).
    """

    # CORE METHODS
    def __init__(self, sample_rate: float, offset_hz: float,
                 target_rate: float = CHANNEL_TARGET_RATE, cutoff_hz: float = CHANNEL_CUTOFF_HZ,
                 transition_hz: float = CHANNEL_TRANSITION_HZ) -> None:
        """Channelizer ctor: design the filter and reset the streaming state.

        Args:
            sample_rate: The wideband stream's sample rate, in samples per second.  Use the SDR's
                actual rate (Sdr.actual_settings), not the requested one.
            offset_hz: The channel frequency minus the wideband stream's center frequency, in Hz
                (e.g., channel_freq - sdr.actual_settings.center_freq).
            target_rate: [OPTIONAL] The channel sample rate to aim for.  The decimation must be a
                whole number, so channel_rate is the closest sample_rate / N to target_rate.
            cutoff_hz: [OPTIONAL] The channel filter's passband edge, in Hz.
            transition_hz: [OPTIONAL] The channel filter's transition width, in Hz.

        Raises:
            ValueError: A non-positive rate, a channel that doesn't fit inside the wideband
                stream, or a filter too wide for the channel rate (it would alias).
        """
        # INPUT VALIDATION
        if sample_rate <= 0 or target_rate <= 0:
            raise ValueError(f'Sample rates must be positive: sample_rate={sample_rate}, '
                             f'target_rate={target_rate}')
        if abs(offset_hz) + cutoff_hz >= sample_rate / 2:
            raise ValueError(f'A channel at {offset_hz} Hz with a {cutoff_hz} Hz passband does not '
                             f'fit within +/-{sample_rate / 2} Hz')

        # PUBLIC ATTRIBUTES
        self.offset_hz = offset_hz                                  # Channel offset, Hz
        self.decimation = max(1, round(sample_rate / target_rate))  # Keep 1 of every N samples
        self.channel_rate = sample_rate / self.decimation           # Output sample rate, S/s

        # The filter's stopband must end below the channel rate's Nyquist frequency, or
        # out-of-channel signals fold back into the channel when decimating
        if cutoff_hz + transition_hz > self.channel_rate / 2:
            raise ValueError(f'The filter stopband edge ({cutoff_hz + transition_hz} Hz) must be '
                             f'at most half the channel rate ({self.channel_rate / 2} Hz)')

        # PRIVATE ATTRIBUTES
        self._taps = design_lowpass(sample_rate, cutoff_hz, transition_hz)  # Filter coefficients
        self._phase_step = -2 * math.pi * offset_hz / sample_rate           # Mixer rad/sample
        # Streaming state, carried between chunks (set by reset())
        self._phase = 0.0          # Mixer phase of the next sample, radians
        self._filter_state = None  # The filter's history: lfilter's zi
        self._next_index = 0       # Index, within the next chunk, of the next sample to keep
        self.reset()

    # PUBLIC METHODS
    # In alphabetical order
    def process_chunk(self, chunk: np.ndarray) -> np.ndarray:
        """Channelize the next chunk of the wideband stream.

        Args:
            chunk: The next consecutive chunk of complex wideband samples, any length.

        Returns:
            The channel's complex64 samples at self.channel_rate, centered on 0 Hz: about
            len(chunk) / self.decimation of them.
        """
        # LOCAL VARIABLES
        num_samples = len(chunk)  # Samples in this chunk
        phases = None             # Mixer phase for each sample in this chunk, radians
        mixed = None              # chunk shifted so the channel is at 0 Hz
        filtered = None           # mixed, low-pass filtered to the channel
        channel = None            # Return value

        # MIX IT: shift the channel to 0 Hz
        phases = self._phase + self._phase_step * np.arange(num_samples)
        mixed = chunk * np.exp(1j * phases)
        self._phase = (self._phase + self._phase_step * num_samples) % (2 * math.pi)

        # FILTER IT: keep only the channel
        filtered, self._filter_state = signal.lfilter(self._taps, 1.0, mixed,
                                                      zi=self._filter_state)

        # DECIMATE IT: keep every decimation-th sample, continuing the count from the last chunk
        channel = filtered[self._next_index::self.decimation].astype(np.complex64)
        self._next_index = (self._next_index - num_samples) % self.decimation

        # DONE
        return channel

    def reset(self) -> None:
        """Forget the streaming state, so the next chunk is treated as the start of a new stream.

        Call it when the input is no longer continuous with what came before (e.g., after
        retuning the SDR).  Not needed after an overflow: the brief transient it causes is
        harmless.
        """
        self._phase = 0.0
        self._filter_state = np.zeros(len(self._taps) - 1, dtype=np.complex128)
        self._next_index = 0
