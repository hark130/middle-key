"""Radio sub-package specific constants."""

# Standard Imports
from typing import Final
# Third Party Imports
# Local Imports

# Radio (SDR) defaults
RADIO_ANTENNA: Final[str] = "RX2"            # USRP B2xx receive port
RADIO_CHANNEL: Final[int] = 0                # Receive channel (single-channel SDRs only have 0)
RADIO_CHUNK_LEN: Final[int] = 1 << 14        # Samples per yielded chunk: ~68 ms at 240 kS/s
RADIO_DEVICE_ARGS: Final[str] = ""           # Device-specific selector; "" = first one found
RADIO_GAIN_DB: Final[float] = 40.0           # RF gain; the B2xx range is roughly 0-76 dB
RADIO_OFFSET_HZ: Final[float] = 50_000.0     # Tune this far below the channel, off the DC spike
RADIO_SAMPLE_RATE: Final[float] = 240_000.0  # Samples per second: 5 x the 48 kS/s audio rate
RADIO_TIMEOUT_S: Final[float] = 1.0          # Longest wait for samples before reporting a timeout
# USRP (UHD) specifics
USRP_CPU_FORMAT: Final[str] = "fc32"         # Samples in host memory: complex float32 (complex64)
USRP_LO_LOCK_TIMEOUT_S: Final[float] = 1.0   # Longest wait for the tuner to lock after tuning
USRP_OTW_FORMAT: Final[str] = "sc16"         # Samples over the wire (USB): complex int16
