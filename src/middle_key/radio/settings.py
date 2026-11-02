"""Defines the RadioSettings dataclass."""

# Standard Imports
from dataclasses import dataclass
# Third Party Imports
# Local Imports
from middle_key.constants import CLI_GAIN_DEFAULT
from middle_key.radio.constants import RADIO_ANTENNA, RADIO_SAMPLE_RATE


@dataclass(frozen=True)
class RadioSettings:
    """How to configure the SDR.

    Attributes:
        center_freq: The RF frequency, in Hz, to tune to.  Tune off the channel (e.g., the channel
            minus RADIO_OFFSET_HZ) so the SDR's DC spike doesn't land on it.
        sample_rate: [OPTIONAL] Samples per second.
        gain: [OPTIONAL] RF gain in dB.  Automatic gain control is always turned off, so levels
            stay comparable for the squelch.
        antenna: [OPTIONAL] The receive port, or None to keep the device's default.
        device_args: [OPTIONAL] The SoapySDR device to open, e.g., 'driver=uhd'.
    """

    center_freq: float                       # RF frequency to tune to, Hz
    sample_rate: float = RADIO_SAMPLE_RATE   # Samples per second
    gain: float = CLI_GAIN_DEFAULT           # RF gain, dB
    antenna: str | None = RADIO_ANTENNA      # Receive port, or None for the default
