"""Common functionality for Universal Software Radio Peripheral (USRP) devices.

Wraps the UHD Python API for MIKE's Sdr interface.  Developed against the B200 series (B206mini).
UHD's Python bindings come with UHD itself, not PyPI (e.g., Debian/Ubuntu: python3-uhd).
Check the radio is visible with:
    uhd_find_devices
"""

# Standard Imports
from dataclasses import replace
import logging
import time
# Third Party Imports
import numpy as np
import uhd  # pylint: disable=import-error
# Local Imports
from middle_key.radio.constants import (RADIO_CHANNEL, RADIO_TIMEOUT_S, USRP_CPU_FORMAT,
                                        USRP_LO_LOCK_TIMEOUT_S, USRP_OTW_FORMAT)
from middle_key.radio.sdr import Sdr
from middle_key.radio.settings import RadioSettings


class UsrpSdr(Sdr):
    """An Ettus USRP, through UHD.  See Sdr for usage."""

    # CORE METHODS
    def __init__(self, settings: RadioSettings) -> None:
        """UsrpSdr ctor.  Nothing touches the hardware until open()."""
        super().__init__(settings)
        self._usrp = None         # uhd.usrp.MultiUSRP: the opened device
        self._streamer = None     # uhd RX streamer, created by _open_device()
        self._metadata = None     # uhd.types.RXMetadata: filled in by each recv()
        self._recv_buffer = None  # (1, max samples per packet) complex64 receive buffer

    # HARDWARE HOOKS
    # In alphabetical order
    def _close_device(self) -> None:
        """Release the USRP.  UHD has no explicit close: dropping the references releases it."""
        self._streamer = None
        self._usrp = None

    def _open_device(self, settings: RadioSettings) -> RadioSettings:
        """Open the USRP, apply settings, and return the settings it actually applied.

        Raises:
            RuntimeError: UHD can't find or configure the USRP (e.g., it isn't plugged in).
        """
        # LOCAL VARIABLES
        stream_args = None  # Formats and channels for the RX streamer
        actual = None       # Return value: settings the USRP applied

        # CONFIGURE IT
        self._usrp = uhd.usrp.MultiUSRP(settings.device_args)
        self._usrp.set_rx_rate(settings.sample_rate, RADIO_CHANNEL)
        self._usrp.set_rx_freq(uhd.types.TuneRequest(settings.center_freq), RADIO_CHANNEL)
        self._usrp.set_rx_agc(False, RADIO_CHANNEL)
        self._usrp.set_rx_gain(settings.gain, RADIO_CHANNEL)
        if settings.antenna is not None:
            self._usrp.set_rx_antenna(settings.antenna, RADIO_CHANNEL)
        self._wait_for_lo_lock()

        # SET UP STREAMING
        stream_args = uhd.usrp.StreamArgs(USRP_CPU_FORMAT, USRP_OTW_FORMAT)
        stream_args.channels = [RADIO_CHANNEL]
        self._streamer = self._usrp.get_rx_stream(stream_args)
        self._metadata = uhd.types.RXMetadata()
        self._recv_buffer = np.zeros((1, self._streamer.get_max_num_samps()), dtype=np.complex64)

        # READ IT BACK
        actual = replace(settings,
                         sample_rate=self._usrp.get_rx_rate(RADIO_CHANNEL),
                         center_freq=self._usrp.get_rx_freq(RADIO_CHANNEL),
                         gain=self._usrp.get_rx_gain(RADIO_CHANNEL),
                         antenna=self._usrp.get_rx_antenna(RADIO_CHANNEL))

        # DONE
        return actual

    def _read_samples(self) -> np.ndarray:
        """Receive one packet of samples.  The returned view is reused by the next call.

        Overflows (the computer didn't keep up, so the USRP dropped samples; UHD also prints
        "O") and timeouts are logged, and return whatever samples did arrive.

        Raises:
            RuntimeError: Any other UHD receive error.
        """
        # LOCAL VARIABLES
        error_codes = uhd.types.RXMetadataErrorCode  # Shorthand for the error code enum
        num_received = 0                             # Samples received into self._recv_buffer

        # RECEIVE IT
        num_received = self._streamer.recv(self._recv_buffer, self._metadata, RADIO_TIMEOUT_S)
        if self._metadata.error_code == error_codes.overflow:
            logging.warning("\nUSRP overflow: samples were dropped")
        elif self._metadata.error_code == error_codes.timeout:
            logging.warning("\nUSRP timeout: no samples for %.1f s", RADIO_TIMEOUT_S)
        elif self._metadata.error_code != error_codes.none:
            raise RuntimeError(f"\nUSRP receive failed: {self._metadata.strerror()}")

        # DONE
        return self._recv_buffer[0, :num_received]

    def _start_stream(self) -> None:
        """Start continuous streaming."""
        # LOCAL VARIABLES
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)  # Start command

        # START IT
        stream_cmd.stream_now = True
        self._streamer.issue_stream_cmd(stream_cmd)

    def _stop_stream(self) -> None:
        """Stop continuous streaming, then drain samples already in flight.

        Draining keeps stale samples from showing up at the start of the next stream.
        """
        self._streamer.issue_stream_cmd(uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont))
        while self._streamer.recv(self._recv_buffer, self._metadata, 0.1) > 0:
            pass

    # PRIVATE METHODS
    # In alphabetical order
    def _wait_for_lo_lock(self) -> None:
        """Wait for the tuner's local oscillator (LO) to lock onto the new frequency.

        Samples taken before the LO locks are at the wrong frequency.  Logs a warning, instead of
        raising, if it doesn't lock within USRP_LO_LOCK_TIMEOUT_S or the device has no lo_locked
        sensor.
        """
        # LOCAL VARIABLES
        deadline = time.monotonic() + USRP_LO_LOCK_TIMEOUT_S  # When to stop waiting
        is_locked = False                                     # Has the LO locked?

        # WAIT FOR IT
        if "lo_locked" in self._usrp.get_rx_sensor_names(RADIO_CHANNEL):
            while not is_locked and time.monotonic() < deadline:
                is_locked = self._usrp.get_rx_sensor("lo_locked", RADIO_CHANNEL).to_bool()
                if not is_locked:
                    time.sleep(0.01)
            if not is_locked:
                logging.warning("USRP LO did not lock within %.1f s", USRP_LO_LOCK_TIMEOUT_S)
        else:
            logging.warning("USRP has no lo_locked sensor; not waiting for the LO to lock")
