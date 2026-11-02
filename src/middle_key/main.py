"""Executes Middle Key (MIKE)."""


# Standard Imports
import logging
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.channelizer import Channelizer
from middle_key.constants import CLI_DEBUG, CLI_FREQ, CLI_GAIN, EXIT_FAILURE, EXIT_SUCCESS
from middle_key.dsp import convert_power_to_db
from middle_key.parse_args import parse_args
from middle_key.radio import RadioSettings, create_sdr
from middle_key.radio.constants import RADIO_OFFSET_HZ


def main() -> int:
    """Listen to one channel and show its power, live, until Ctrl+C.

    Returns:
        EXIT_SUCCESS, or EXIT_FAILURE if the radio couldn't be opened or failed while streaming.
    """
    # LOCAL VARIABLES
    exit_code = EXIT_SUCCESS                # Return value
    args = parse_args()                     # CLI args
    debug = getattr(args, CLI_DEBUG)        # Debug mode?
    channel_freq = getattr(args, CLI_FREQ)  # Channel to listen to, Hz
    settings = None                         # Requested radio configuration
    channelizer = None                      # Selects the channel from the SDR's wideband IQ
    channel = None                          # One chunk's worth of channel samples
    power_db = 0.0                          # Average power of the channel chunk, dBFS

    # SETUP
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING,
                        format='%(levelname)s: %(message)s')
    settings = RadioSettings(center_freq=channel_freq - RADIO_OFFSET_HZ,
                             gain=getattr(args, CLI_GAIN))

    # LISTEN
    try:
        with create_sdr(settings) as sdr:
            print(f'Listening on {channel_freq / 1e6:.3f} MHz: SDR tuned to '
                  f'{sdr.actual_settings.center_freq / 1e6:.3f} MHz at '
                  f'{sdr.actual_settings.sample_rate:.0f} S/s, '
                  f'gain {sdr.actual_settings.gain:.1f} dB (Ctrl+C to stop)')
            channelizer = Channelizer(sample_rate=sdr.actual_settings.sample_rate,
                                      offset_hz=channel_freq - sdr.actual_settings.center_freq)
            print(f'Channel: {channelizer.offset_hz / 1e3:+.3f} kHz from center, decimated by '
                  f'{channelizer.decimation} to {channelizer.channel_rate:.0f} S/s')
            for chunk in sdr.stream_samples():
                channel = channelizer.process_chunk(chunk)
                power_db = float(convert_power_to_db(np.mean(np.abs(channel)**2)))
                print(f'\rChannel power: {power_db:7.1f} dBFS', end='', flush=True)
    except KeyboardInterrupt:
        print('\nStopped')
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as err:
        exit_code = EXIT_FAILURE
        print(f'\n{repr(err)}')
        if debug:
            raise err

    # DONE
    return exit_code
