"""Defines the BurstDetector class and the BurstEvent it reports: MIKE's squelch decisions.

The detector decides when transmissions start and end; it never keeps samples.  Each decision is
a BurstEvent that points at the exact channel-stream sample where it happened.  Events arrive
late by design: a start is only reported once the signal has stayed up for the confirm time, and
an end only once the hang time has passed, so sample_index usually points into an earlier chunk.

The contract (what BurstRecorder relies on):
    1. Events alternate: OPENED, CLOSED, OPENED, ... starting with OPENED.
    2. Each event's sample_index is greater than the previous event's.
    3. OPENED points back at most the confirm time; CLOSED at most the hang time (plus a frame).
    4. Every OPENED is a real transmission: the signal stayed up for at least the confirm time.

USAGE:
    detector = BurstDetector(channel_rate=48_000)
    for chunk in sdr.stream_samples():
        events = detector.process_chunk(channelizer.process_chunk(chunk))
"""

# Standard Imports
from collections import deque
from dataclasses import dataclass
from enum import Enum
import math
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.constants import (BURST_CLOSE_DB, BURST_CONFIRM_S, BURST_FLOOR_PERCENTILE,
                                  BURST_FLOOR_WINDOW_S, BURST_FRAME_S, BURST_HANG_S,
                                  BURST_OPEN_DB, BURST_WARMUP_S)
from middle_key.dsp import convert_power_to_db


class BurstEventType(Enum):
    """What happened to the channel."""
    OPENED = "opened"  # A transmission started
    CLOSED = "closed"  # A transmission ended


@dataclass(frozen=True)
class BurstEvent:
    """One squelch decision, reported by BurstDetector.process_chunk().

    Attributes:
        event_type: Whether a transmission started or ended.
        sample_index: The channel-stream sample where it happened, counted from the first sample
            the detector ever saw (not from the start of the current chunk).
    """

    event_type: BurstEventType  # What happened
    sample_index: int           # Where it happened: absolute position in the channel stream


class BurstDetector:  # pylint: disable=too-many-instance-attributes
    """Decide when transmissions start and end, from a stream of channel chunks.

    Power is measured over short frames and compared to an adaptive noise floor (a low
    percentile of recent frame powers), so the thresholds follow the radio's gain and the
    channel's noise instead of being fixed.

    Attributes:
        floor_db: The current noise floor estimate, in dBFS (None during warm-up).
        is_open: True while a transmission is in progress (from OPENED until CLOSED).
        max_lookback_len: The farthest, in samples, an OPENED event's sample_index can point
            before the start of the chunk that reported it.  Whatever keeps samples for the
            detector's events (e.g., BurstRecorder) needs at least this much history.
    """

    # CORE METHODS
    def __init__(self, channel_rate: float, open_db: float = BURST_OPEN_DB,
                 close_db: float = BURST_CLOSE_DB, confirm_s: float = BURST_CONFIRM_S,
                 hang_s: float = BURST_HANG_S) -> None:
        """BurstDetector ctor.

        Args:
            channel_rate: The channel's sample rate in samples per second.
            open_db: [OPTIONAL] Start confirming a burst when power is this far above the floor.
            close_db: [OPTIONAL] Count power as quiet when it's less than this far above the
                floor.  Must be below open_db; the gap is the hysteresis.
            confirm_s: [OPTIONAL] Power must stay up this long before OPENED is reported.
            hang_s: [OPTIONAL] Power must stay quiet this long before CLOSED is reported.

        Raises:
            ValueError: A non-positive rate or time, or close_db isn't below open_db.
        """
        # INPUT VALIDATION
        if channel_rate <= 0 or confirm_s <= 0 or hang_s <= 0:
            raise ValueError(f"Rates and times must be positive: channel_rate={channel_rate}, "
                             f"confirm_s={confirm_s}, hang_s={hang_s}")
        if close_db >= open_db:
            raise ValueError(f"close_db ({close_db}) must be below open_db ({open_db})")

        # SETTINGS, converted to samples and frames
        self._open_db = open_db                                          # Open threshold, dB
        self._close_db = close_db                                        # Close threshold, dB
        self._frame_len = max(1, round(BURST_FRAME_S * channel_rate))    # Samples per frame
        self._confirm_len = round(confirm_s * channel_rate)              # Confirm time, samples
        self._hang_len = round(hang_s * channel_rate)                    # Hang time, samples
        self._warmup_frames = math.ceil(BURST_WARMUP_S / BURST_FRAME_S)  # Frames before detecting
        # How far back an OPENED can point: the confirm time, rounded up to a whole frame
        self.max_lookback_len = self._confirm_len + self._frame_len
        # Recent frame powers, for the noise floor (oldest drop off automatically)
        self._floor_history = deque(maxlen=math.ceil(BURST_FLOOR_WINDOW_S / BURST_FRAME_S))

        # STREAMING STATE (set by reset())
        self.floor_db = None      # Noise floor estimate, dBFS (public)
        self.is_open = False      # Is a transmission in progress? (public)
        self._leftover = None     # Samples short of a full frame
        self._next_index = 0      # Absolute index of the next frame
        self._rise_index = None   # Where power rose, while confirming
        self._quiet_index = None  # Where power fell, while open
        self.reset()

    # PUBLIC METHODS
    # In alphabetical order
    def process_chunk(self, channel: np.ndarray) -> list[BurstEvent]:
        """Measure the next chunk of the channel stream and report any squelch decisions.

        Args:
            channel: The next consecutive chunk of channel samples (e.g., from a Channelizer).

        Returns:
            The events decided during this chunk, oldest first: usually an empty list.
        """
        # LOCAL VARIABLES
        samples = np.concatenate((self._leftover, channel))  # Leftover samples, then this chunk
        num_frames = len(samples) // self._frame_len         # Complete frames available
        frame_powers = None                                  # Power of each frame, dBFS
        events = []                                          # Return value

        # MEASURE IT: power of each complete frame; keep the remainder for the next chunk
        frame_powers = convert_power_to_db(np.mean(
            np.abs(samples[:num_frames * self._frame_len].reshape(num_frames,
                                                                  self._frame_len))**2,
            axis=1))
        self._leftover = samples[num_frames * self._frame_len:]

        # UPDATE THE NOISE FLOOR, once per chunk
        self._floor_history.extend(frame_powers)
        if len(self._floor_history) >= self._warmup_frames:
            self.floor_db = float(np.percentile(self._floor_history, BURST_FLOOR_PERCENTILE))

        # DECIDE: step each frame through the squelch logic
        for power_db in frame_powers:
            if self.floor_db is not None:
                events.extend(self._check_frame(power_db - self.floor_db))
            self._next_index += self._frame_len

        # DONE
        return events

    def reset(self) -> None:
        """Start over: forget the noise floor, any burst in progress, and the sample count.

        Call it when the input is no longer continuous with what came before (e.g., after
        retuning the SDR).  Detection resumes after the warm-up time.
        """
        self.floor_db = None
        self.is_open = False
        self._floor_history.clear()
        self._leftover = np.zeros(0, dtype=np.complex64)
        self._next_index = 0
        self._rise_index = None
        self._quiet_index = None

    # PRIVATE METHODS
    def _check_frame(self, above_floor_db: float) -> list[BurstEvent]:
        """Run one frame through the squelch logic.

        Args:
            above_floor_db: The frame's power relative to the noise floor, in dB.

        Returns:
            A list holding the OPENED or CLOSED event this frame triggered, or an empty list.
        """
        # LOCAL VARIABLES
        frame_end = self._next_index + self._frame_len  # Index just past this frame
        events = []                                     # Return value

        # NOT OPEN: confirm a rise, then report where it started
        if not self.is_open:
            if above_floor_db < self._close_db:
                self._rise_index = None              # Fell back to quiet: not a burst
            elif self._rise_index is None and above_floor_db >= self._open_db:
                self._rise_index = self._next_index  # Rose above open: start confirming
            if self._rise_index is not None and frame_end - self._rise_index >= self._confirm_len:
                events.append(BurstEvent(BurstEventType.OPENED, self._rise_index))
                self.is_open = True
                self._rise_index = None
        # OPEN: wait out the hang time, then report where the quiet started
        else:
            if above_floor_db >= self._close_db:
                self._quiet_index = None              # Signal is back: keep going
            elif self._quiet_index is None:
                self._quiet_index = self._next_index  # Went quiet: start the hang timer
            if self._quiet_index is not None and frame_end - self._quiet_index >= self._hang_len:
                events.append(BurstEvent(BurstEventType.CLOSED, self._quiet_index))
                self.is_open = False
                self._quiet_index = None

        # DONE
        return events
