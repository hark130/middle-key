"""Defines the RadioType enum and the RadioSettings dataclass."""

# Standard Imports
from dataclasses import dataclass
from enum import Enum
# Third Party Imports
# Local Imports
from middle_key.radio.constants import (RADIO_ANTENNA, RADIO_DEVICE_ARGS,
                                        RADIO_FREQ_CORRECTION_PPM, RADIO_GAIN_DB,
                                        RADIO_SAMPLE_RATE)


class RadioType(Enum):
    """The SDR families MIKE supports."""
    RTLSDR = "rtlsdr"  # RTL2832U-based dongles (RTL-SDR) through pyrtlsdr
    USRP = "usrp"      # Ettus USRP (B200 series, e.g., B206mini) through UHD


@dataclass(frozen=True)
class RadioSettings:
    """How to configure the SDR.

    Attributes:
        center_freq: The RF frequency, in Hz, to tune to.  Tune off the channel (e.g., the channel
            minus RADIO_OFFSET_HZ) so the SDR's DC spike doesn't land on it.
        sample_rate: [OPTIONAL] Samples per second.
        gain: [OPTIONAL] RF gain in dB.  Automatic gain control is always turned off, so levels
            stay comparable for the squelch.
        antenna: [OPTIONAL] The receive port, or None to keep the device's default.  Radios with
            a single input (e.g., RTL-SDR) ignore it.
        radio_type: [OPTIONAL] Which SDR family to use (see create_sdr()).
        device_args: [OPTIONAL] Selects a specific device, in the radio's own format
            (e.g., "type=b200" or "serial=31F5A6B" for UHD; "index=1" or "serial=00000001" for
            RTL-SDR).  "" uses the first device found.
        freq_correction_ppm: [OPTIONAL] The radio's oscillator error, in parts per million, for
            radios that correct it in hardware (RTL-SDR).  Others ignore it.
    """

    center_freq: float                                    # RF frequency to tune to, Hz
    sample_rate: float = RADIO_SAMPLE_RATE                # Samples per second
    gain: float = RADIO_GAIN_DB                           # RF gain, dB
    antenna: str | None = RADIO_ANTENNA                   # Receive port, or None for the default
    radio_type: RadioType = RadioType.USRP                # SDR family
    device_args: str = RADIO_DEVICE_ARGS                  # Device selector; "" = the first found
    freq_correction_ppm: int = RADIO_FREQ_CORRECTION_PPM  # Oscillator error to correct, ppm
