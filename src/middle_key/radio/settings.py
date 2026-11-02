"""Defines the RadioType enum and the RadioSettings dataclass."""

# Standard Imports
from dataclasses import dataclass
from enum import Enum
# Third Party Imports
# Local Imports
from middle_key.radio.constants import (RADIO_ANTENNA, RADIO_DEVICE_ARGS, RADIO_GAIN_DB,
                                        RADIO_SAMPLE_RATE)


class RadioType(Enum):
    """The SDR families MIKE supports."""
    USRP = "usrp"  # Ettus USRP (B200 series, e.g., B206mini) through UHD


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
        radio_type: [OPTIONAL] Which SDR family to use (see create_sdr()).
        device_args: [OPTIONAL] Selects a specific device, in the radio's own format
            (e.g., "type=b200" or "serial=31F5A6B" for UHD).  "" uses the first device found.
    """

    center_freq: float                      # RF frequency to tune to, Hz
    sample_rate: float = RADIO_SAMPLE_RATE  # Samples per second
    gain: float = RADIO_GAIN_DB             # RF gain, dB
    antenna: str | None = RADIO_ANTENNA     # Receive port, or None for the default
    radio_type: RadioType = RadioType.USRP  # SDR family
    device_args: str = RADIO_DEVICE_ARGS    # Device selector, or "" for the first found
