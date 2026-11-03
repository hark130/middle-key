"""Defines Sdr, the radio-independent interface every supported SDR implements.

Sdr owns everything that's the same for every radio: opening and closing, the context manager,
starting and stopping the stream, and assembling whatever the hardware delivers into fixed-size
chunks.  A subclass only wraps its hardware's API, by implementing five small hooks:
    _open_device(), _close_device(), _start_stream(), _read_samples(), _stop_stream()

USAGE:
    from middle_key.radio import RadioSettings, create_sdr

    with create_sdr(RadioSettings(center_freq=119.75e6)) as sdr:
        for chunk in sdr.stream_samples():
            ...  # chunk: np.ndarray of complex64 at sdr.actual_settings.sample_rate
"""

# Standard Imports
from abc import ABC, abstractmethod
from typing import Iterator
import logging
import math
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.radio.constants import RADIO_CHUNK_LEN
from middle_key.radio.settings import RadioSettings


class Sdr(ABC):
    """A software-defined radio that streams complex baseband samples.

    Open it with a with statement (or open()/close()), then iterate over stream_samples().

    Attributes:
        requested_settings: The settings this SDR was created with.
        actual_settings: The settings the hardware applied, read back by open(); None until
            then.  Downstream code (e.g., the channelizer) should use these, not the requested
            ones: hardware can't always provide exactly what was asked for.
    """

    # CORE METHODS
    def __init__(self, settings: RadioSettings) -> None:
        """Sdr ctor.  Nothing touches the hardware until open()."""
        self.requested_settings = settings  # Settings this SDR was created with
        self.actual_settings = None         # Settings the hardware applied, set by open()
        self._is_streaming = False          # Is a stream running?

    def __enter__(self) -> 'Sdr':
        """Open the SDR for a with statement."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Close the SDR at the end of a with statement, even if an exception was raised."""
        self.close()

    # PUBLIC METHODS
    # In alphabetical order
    def close(self) -> None:
        """Stop any running stream and release the hardware.  Safe to call more than once."""
        if self._is_streaming:
            self._stop_stream()
            self._is_streaming = False
        if self.actual_settings is not None:
            self._close_device()
            self.actual_settings = None

    def open(self) -> RadioSettings:
        """Open and configure the hardware, then read back the settings it actually applied.

        Returns:
            The actual settings (also stored in self.actual_settings).

        Raises:
            RuntimeError: The hardware can't be found or configured.
        """
        # LOCAL VARIABLES
        requested = self.requested_settings  # Shorthand for the requested settings

        # OPEN IT
        self.actual_settings = self._open_device(requested)
        if self.actual_settings.sample_rate != requested.sample_rate:
            if not math.isclose(self.actual_settings.sample_rate, requested.sample_rate):
                logging.warning('Requested %.0f S/s but the SDR is running at %.0f S/s',
                                requested.sample_rate, self.actual_settings.sample_rate)

        # DONE
        return self.actual_settings

    def stream_samples(self, chunk_len: int = RADIO_CHUNK_LEN) -> Iterator[np.ndarray]:
        """Stream samples, one fixed-size chunk at a time, until the caller stops iterating.

        The stream starts on the first next() and stops when iteration ends (break, return, an
        exception, or Ctrl+C).  Hardware delivers samples in whatever amounts it likes; they're
        packed into chunks with nothing dropped or repeated, so consecutive chunks are
        continuous unless the hardware itself dropped samples (see _read_samples()).

        Args:
            chunk_len: [OPTIONAL] The number of samples in each yielded chunk.

        Yields:
            np.ndarray of chunk_len complex64 samples, scaled so full scale is a magnitude of 1.0.
            Each chunk is a new array, so it's safe to keep.

        Raises:
            RuntimeError: The SDR isn't open, or the hardware reported an unrecoverable error.
            ValueError: chunk_len is not positive.
        """
        # LOCAL VARIABLES
        chunk = None    # The chunk being filled
        filled = 0      # Number of samples in chunk so far
        samples = None  # Samples from one hardware read
        start = 0       # Index of the next unused sample in samples
        take = 0        # Number of samples copied from samples into chunk at once

        # INPUT VALIDATION
        if self.actual_settings is None:
            raise RuntimeError('The SDR must be opened before streaming (see open())')
        if chunk_len <= 0:
            raise ValueError(f'The "chunk_len" argument must be positive, not {chunk_len}')

        # STREAM IT
        self._start_stream()
        self._is_streaming = True
        try:
            chunk = np.empty(chunk_len, dtype=np.complex64)
            while True:
                samples = self._read_samples()
                start = 0
                while start < len(samples):
                    take = min(chunk_len - filled, len(samples) - start)
                    chunk[filled:filled + take] = samples[start:start + take]
                    filled += take
                    start += take
                    if filled == chunk_len:
                        yield chunk
                        chunk = np.empty(chunk_len, dtype=np.complex64)
                        filled = 0
        finally:
            if self._is_streaming:
                self._stop_stream()
                self._is_streaming = False

    # HARDWARE HOOKS: each subclass implements these for its radio's API
    # In alphabetical order
    @abstractmethod
    def _close_device(self) -> None:
        """Release the hardware.  Called once, after any stream has been stopped."""

    @abstractmethod
    def _open_device(self, settings: RadioSettings) -> RadioSettings:
        """Open the hardware, apply settings, and return the settings it actually applied.

        Raises:
            RuntimeError: The hardware can't be found or configured.
        """

    @abstractmethod
    def _read_samples(self) -> np.ndarray:
        """Read whatever samples are ready: complex64, full scale = 1.0.

        Return an empty array, after logging why, when a read gets no samples for a recoverable
        reason (e.g., an overflow or a timeout).  The returned array may be reused by the next
        call, so the caller must copy what it keeps.

        Raises:
            RuntimeError: An unrecoverable hardware error.
        """

    @abstractmethod
    def _start_stream(self) -> None:
        """Start streaming samples from the hardware."""

    @abstractmethod
    def _stop_stream(self) -> None:
        """Stop streaming samples from the hardware."""
