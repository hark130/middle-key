"""Defines the BurstRecorder class and the Burst it produces: MIKE's sample keeper.

The recorder keeps channel samples and acts on BurstDetector's decisions; it never decides
anything itself.  It always keeps a short history of recent chunks, because the detector's
events point back in time (see burst_detector.py), and collects every chunk while a
transmission is open.  On CLOSED it cuts out exactly one complete transmission and returns it.
A transmission still open when the stream stops is never returned, so there are no partial
bursts.

USAGE (normally through ChannelMonitor, which keeps the recorder and detector in step):
    recorder = BurstRecorder(channel_rate=48_000, channel_freq=119.8e6,
                             lookback_len=detector.max_lookback_len)
    for chunk in sdr.stream_samples():
        channel = channelizer.process_chunk(chunk)
        for burst in recorder.process_chunk(channel, detector.process_chunk(channel)):
            ...  # burst.samples: one complete transmission
"""

# Standard Imports
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.burst_detector import BurstEvent, BurstEventType
from middle_key.constants import BURST_PAD_S


@dataclass(frozen=True)
class Burst:
    """One complete transmission on one channel.

    Attributes:
        start_time: The UTC time of the first sample (including the leading pad).
        channel_freq: The channel's RF frequency, in Hz.
        sample_rate: The samples' rate, in samples per second.
        samples: The transmission's complex baseband channel samples, padded at both ends.
    """

    start_time: datetime  # UTC time of samples[0]
    channel_freq: float   # Channel frequency, Hz
    sample_rate: float    # Samples per second
    samples: np.ndarray   # Complex baseband samples

    def calculate_duration(self) -> float:
        """Calculate the burst's duration in seconds."""
        return len(self.samples) / self.sample_rate


class BurstRecorder:  # pylint: disable=too-many-instance-attributes
    """Keep a channel's samples and cut out each complete transmission the detector reports.

    Each process_chunk() call must get the same chunk BurstDetector.process_chunk() just saw,
    plus the events it returned, so both count samples identically.
    """

    # CORE METHODS
    def __init__(self, channel_rate: float, channel_freq: float, lookback_len: int,
                 pad_s: float = BURST_PAD_S) -> None:
        """BurstRecorder ctor.

        Args:
            channel_rate: The channel's sample rate in samples per second.
            channel_freq: The channel's RF frequency, in Hz (copied into each Burst).
            lookback_len: How far, in samples, the detector's OPENED events can point back:
                use its max_lookback_len.
            pad_s: [OPTIONAL] Extra audio to keep before and after each transmission.

        Raises:
            ValueError: A non-positive rate, or a negative lookback or pad.
        """
        # INPUT VALIDATION
        if channel_rate <= 0 or lookback_len < 0 or pad_s < 0:
            raise ValueError(f"Bad recorder settings: channel_rate={channel_rate}, "
                             f"lookback_len={lookback_len}, pad_s={pad_s}")

        # SETTINGS
        self._channel_rate = channel_rate            # Samples per second
        self._channel_freq = channel_freq            # Channel frequency, Hz
        self._pad_len = round(pad_s * channel_rate)  # Padding at each end, samples
        # History to keep: as far back as an OPENED can point, plus the pad in front of it
        self._history_len = lookback_len + self._pad_len

        # STREAMING STATE (set by reset())
        self._history = deque()    # (start index, chunk) pairs: recent chunks, oldest first
        self._burst_chunks = None  # (start index, chunk) pairs since OPENED, or None if closed
        self._burst_start = 0      # Absolute index where the current burst's samples begin
        self._next_index = 0       # Absolute index of the next sample to arrive
        self.reset()

    # PUBLIC METHODS
    # In alphabetical order
    def process_chunk(self, channel: np.ndarray, events: list[BurstEvent]) -> list[Burst]:
        """Keep the next chunk, act on the detector's events, and return finished transmissions.

        Args:
            channel: The same channel chunk just given to BurstDetector.process_chunk().
            events: The events that call returned.

        Returns:
            The transmissions that ended during this chunk, oldest first: usually an empty list.
        """
        # LOCAL VARIABLES
        chunk_start = self._next_index  # Absolute index of channel[0]
        bursts = []                     # Return value

        # KEEP IT
        self._next_index += len(channel)
        self._history.append((chunk_start, channel))
        self._trim_history()
        if self._burst_chunks is not None:
            self._burst_chunks.append((chunk_start, channel))

        # ACT ON IT
        for event in events:
            if event.event_type == BurstEventType.OPENED:
                self._start_burst(event.sample_index)
            elif self._burst_chunks is not None:
                bursts.append(self._finish_burst(event.sample_index))

        # DONE
        return bursts

    def reset(self) -> None:
        """Start over: discard the history, any transmission in progress, and the sample count.

        Call it whenever the BurstDetector is reset, so both keep counting samples identically.
        """
        self._history = deque()
        self._burst_chunks = None
        self._burst_start = 0
        self._next_index = 0

    # PRIVATE METHODS
    # In alphabetical order
    def _finish_burst(self, quiet_index: int) -> Burst:
        """Cut out the current transmission, ending pad_s after quiet_index, and package it."""
        # LOCAL VARIABLES
        end = min(quiet_index + self._pad_len, self._next_index)  # Index just past the burst
        first_index = self._burst_chunks[0][0]                    # Index of the first kept chunk
        samples = None                                            # All kept samples, joined
        burst = None                                              # Return value

        # PACKAGE IT: the newest sample arrived just now, so count back from the wall clock
        samples = np.concatenate([chunk for _, chunk in self._burst_chunks])
        burst = Burst(start_time=datetime.now(timezone.utc) -
                      timedelta(seconds=(self._next_index - self._burst_start) /
                                self._channel_rate),
                      channel_freq=self._channel_freq,
                      sample_rate=self._channel_rate,
                      samples=samples[self._burst_start - first_index:end - first_index])
        self._burst_chunks = None

        # DONE
        return burst

    def _start_burst(self, rise_index: int) -> None:
        """Start collecting a transmission that began at rise_index, from the history."""
        # LOCAL VARIABLES
        oldest = self._history[0][0]  # Oldest sample still in the history

        # START IT
        self._burst_start = max(rise_index - self._pad_len, oldest)
        if rise_index - self._pad_len < oldest:
            logging.warning("Burst started before the recorder history; its start is clipped")
        self._burst_chunks = [(start, chunk) for start, chunk in self._history
                              if start + len(chunk) > self._burst_start]

    def _trim_history(self) -> None:
        """Drop chunks that end too far before the newest chunk for any event to reach them.

        Events reported during the newest chunk can point back up to lookback_len samples
        before it starts, and a burst's start is padded by pad_s more, so the history must
        reach that far back from the start of the newest chunk (not from its end).
        """
        # LOCAL VARIABLES
        newest_start = self._history[-1][0]  # Absolute index of the newest chunk's first sample
        oldest_end = 0                       # Absolute index just past the oldest kept chunk

        # TRIM IT
        oldest_end = self._history[0][0] + len(self._history[0][1])
        while newest_start - oldest_end >= self._history_len:
            self._history.popleft()
            oldest_end = self._history[0][0] + len(self._history[0][1])
