"""Defines the ChannelMonitor class: everything MIKE does for one channel.

A ChannelMonitor owns one channel's Channelizer, BurstDetector, and BurstRecorder, and is the only
thing that calls them, so the rules they depend on always hold:
    1. All three see every chunk, in order, and the recorder sees the same channel chunk the
       detector just saw, along with the events it returned.
    2. The recorder keeps as much history as the detector's events can point back into.
    3. All three are reset together, so they agree on sample numbers.

Every ChannelMonitor takes the same wideband chunks, so monitoring several channels covered by
one SDR is a list of monitors.

USAGE:
    monitor = ChannelMonitor(channel_freq=119.8e6, sdr_settings=sdr.actual_settings)
    for chunk in sdr.stream_samples():
        for burst in monitor.process_chunk(chunk):
            ...  # burst: one complete transmission
"""

# Standard Imports
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.burst_detector import BurstDetector
from middle_key.burst_recorder import Burst, BurstRecorder
from middle_key.channelizer import Channelizer
from middle_key.dsp import convert_power_to_db
from middle_key.radio import RadioSettings


class ChannelMonitor:
    """Turn one channel of an SDR's wideband stream into complete transmissions.

    Attributes:
        channel_freq: The channel's RF frequency, in Hz.
        channelizer: Selects the channel from the wideband stream.
        detector: Decides when transmissions start and end; its floor_db and is_open attributes
            show the squelch status.
        recorder: Keeps the channel's samples and cuts out complete transmissions.
        power_db: The latest channel chunk's average power, in dBFS (None before the first).
    """

    # CORE METHODS
    def __init__(self, channel_freq: float, sdr_settings: RadioSettings) -> None:
        """ChannelMonitor ctor: build the channel's pipeline, in step with itself.

        Args:
            channel_freq: The channel's RF frequency, in Hz.  It must lie within the SDR's
                bandwidth (see Channelizer).
            sdr_settings: The SDR's actual settings (Sdr.actual_settings), not the requested
                ones, so the channel's offset and sample rate are exact.

        Raises:
            ValueError: The channel doesn't fit within the SDR's bandwidth, or another setting
                is invalid (see Channelizer, BurstDetector, and BurstRecorder).
        """
        self.channel_freq = channel_freq  # Channel frequency, Hz
        self.channelizer = Channelizer(sample_rate=sdr_settings.sample_rate,
                                       offset_hz=channel_freq - sdr_settings.center_freq)
        self.detector = BurstDetector(channel_rate=self.channelizer.channel_rate)
        self.recorder = BurstRecorder(channel_rate=self.channelizer.channel_rate,
                                      channel_freq=channel_freq,
                                      lookback_len=self.detector.max_lookback_len)
        self.power_db = None  # Latest channel chunk's power, dBFS

    # PUBLIC METHODS
    # In alphabetical order
    def process_chunk(self, wideband_chunk: np.ndarray) -> list[Burst]:
        """Run the next wideband chunk through the channel's pipeline.

        Args:
            wideband_chunk: The next consecutive chunk from the SDR (Sdr.stream_samples()).

        Returns:
            The transmissions on this channel that ended during this chunk, oldest first:
            usually an empty list.
        """
        # LOCAL VARIABLES
        channel = self.channelizer.process_chunk(wideband_chunk)  # This channel's samples
        events = self.detector.process_chunk(channel)             # Squelch decisions
        bursts = self.recorder.process_chunk(channel, events)     # Return value

        # MEASURE IT: for status displays
        self.power_db = float(convert_power_to_db(np.mean(np.abs(channel)**2)))

        # DONE
        return bursts

    def reset(self) -> None:
        """Start the channel over: forget all streaming state, in all three stages at once.

        Call it when the SDR's stream is no longer continuous (e.g., after retuning).  A
        transmission in progress is discarded, and detection resumes after the warm-up time.
        """
        self.channelizer.reset()
        self.detector.reset()
        self.recorder.reset()
        self.power_db = None
