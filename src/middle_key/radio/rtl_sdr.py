"""Common functionality for RTL-SDR (RTL2832U-based) dongles.

Wraps pyrtlsdr for MIKE's Sdr interface.  pyrtlsdr is on PyPI (pip install pyrtlsdr), but it
needs the librtlsdr C library from your OS (e.g., Debian/Ubuntu: sudo apt install rtl-sdr).
Check the dongle is visible with:
    rtl_test

Differences from the USRP worth knowing:
    - One antenna input, so RadioSettings.antenna is ignored.
    - A cheap oscillator, often tens of ppm off: set RadioSettings.freq_correction_ppm.
    - Only some sample rates work: 225,001-300,000 S/s, or 900,001-3,200,000 S/s.
    - Reads are synchronous and can't report overflows: if MIKE falls behind, samples are
      dropped silently.
"""

# Standard Imports
from dataclasses import replace
import logging
# Third Party Imports
from rtlsdr import RtlSdr as PyRtlSdr  # pylint: disable=import-error
import numpy as np
# Local Imports
from middle_key.radio.constants import RTLSDR_READ_LEN
from middle_key.radio.sdr import Sdr
from middle_key.radio.settings import RadioSettings


class RtlSdr(Sdr):
    """An RTL-SDR dongle, through pyrtlsdr.  See Sdr for usage."""

    # CORE METHODS
    def __init__(self, settings: RadioSettings) -> None:
        """RtlSdr ctor.  Nothing touches the hardware until open()."""
        super().__init__(settings)
        self._rtl = None  # pyrtlsdr.RtlSdr: the opened dongle

    # HARDWARE HOOKS
    # In alphabetical order
    def _close_device(self) -> None:
        """Release the dongle."""
        self._rtl.close()
        self._rtl = None

    def _open_device(self, settings: RadioSettings) -> RadioSettings:
        """Open the dongle, apply settings, and return the settings it actually applied.

        Raises:
            OSError: librtlsdr can't open or configure the dongle (e.g., it isn't plugged in, or
                the kernel's TV-tuner driver has claimed it).
            ValueError: settings.device_args isn't "", "index=N", or "serial=S".
        """
        # LOCAL VARIABLES
        actual = None  # Return value: settings the dongle applied

        # OPEN IT
        self._rtl = PyRtlSdr(**self._parse_device_args(settings.device_args))
        try:
            # CONFIGURE IT
            self._rtl.sample_rate = settings.sample_rate
            # librtlsdr rejects "changing" the correction to the value it already has
            if settings.freq_correction_ppm != self._rtl.freq_correction:
                self._rtl.freq_correction = int(settings.freq_correction_ppm)
            self._rtl.center_freq = settings.center_freq
            self._rtl.gain = settings.gain  # Nearest supported gain; also turns the AGC off
            if settings.antenna is not None:
                logging.debug("RTL-SDR has a single input; ignoring antenna=%s", settings.antenna)

            # READ IT BACK
            actual = replace(settings,
                             sample_rate=self._rtl.sample_rate,
                             center_freq=float(self._rtl.center_freq),
                             gain=self._rtl.gain,
                             antenna=None,
                             freq_correction_ppm=self._rtl.freq_correction)
        except Exception:
            self._rtl.close()  # Don't leave a half-configured dongle open
            self._rtl = None
            raise

        # DONE
        return actual

    def _read_samples(self) -> np.ndarray:
        """Read RTLSDR_READ_LEN samples, as complex64.

        Raises:
            RuntimeError: librtlsdr reported a read error (e.g., the dongle was unplugged).
        """
        # LOCAL VARIABLES
        samples = None  # Return value

        # READ IT
        try:
            samples = self._rtl.read_samples(RTLSDR_READ_LEN).astype(np.complex64)
        except OSError as err:
            raise RuntimeError(f"RTL-SDR read failed: {err}") from err

        # DONE
        return samples

    def _start_stream(self) -> None:
        """Start reading: discard one read, which holds stale samples from before streaming."""
        self._read_samples()

    def _stop_stream(self) -> None:
        """Stop reading.  Reads are synchronous, so there's nothing to stop."""

    # PRIVATE METHODS
    # In alphabetical order
    def _parse_device_args(self, device_args: str) -> dict:
        """Translate device_args into pyrtlsdr.RtlSdr() keyword arguments.

        Args:
            device_args: "" for the first dongle, "index=N" for the Nth (from 0), or "serial=S"
                for the one with serial number S (see rtl_test, or rtl_eeprom to set one).

        Returns:
            A dict of keyword arguments for pyrtlsdr.RtlSdr().

        Raises:
            ValueError: device_args isn't in one of those formats.
        """
        # LOCAL VARIABLES
        key, _, value = device_args.partition("=")  # e.g., ("serial", "=", "00000001")
        kwargs = {}                                  # Return value

        # PARSE IT
        if key == "index" and value.isdigit():
            kwargs = {"device_index": int(value)}
        elif key == "serial" and value:
            kwargs = {"serial_number": value}
        elif device_args:
            raise ValueError(f'RTL-SDR device_args must be "", "index=N", or "serial=S", '
                             f'not "{device_args}"')

        # DONE
        return kwargs
