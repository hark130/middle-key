"""Radio sub-package specific constants."""

# Standard Imports
from typing import Final
# Third Party Imports
# Local Imports

# Radio (SDR) defaults
RADIO_ANTENNA: Final[str] = "RX2"             # USRP B2xx receive port
RADIO_CHANNEL: Final[int] = 0                 # Receive channel (single-channel SDRs only have 0)
RADIO_CHUNK_LEN: Final[int] = 1 << 14         # Samples per yielded chunk: ~68 ms at 240 kS/s
# Consider moving middle_key.constants.CLI_GAIN_DEFAULT here instead
RADIO_OFFSET_HZ: Final[float] = 50_000.0      # Tune this far below the channel, off the DC spike
RADIO_SAMPLE_RATE: Final[float] = 240_000.0   # Samples per second: 5 x the 48 kS/s audio rate
RADIO_TIMEOUT_US: Final[int] = 1_000_000      # readStream() timeout: 1 s, in microseconds
