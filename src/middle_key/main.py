"""Executes Middle Key (MIKE)."""


# Standard Imports
from pathlib import Path
import logging
# Third Party Imports
# Local Imports
from middle_key.burst_recorder import Burst
from middle_key.channel_monitor import ChannelMonitor
from middle_key.constants import (CLI_DEBUG, CLI_FREQ, CLI_GAIN, CLI_OUT, CLI_PPM, CLI_RADIO,
                                  EXIT_FAILURE, EXIT_SUCCESS)
from middle_key.demod import extract_normal_audio
from middle_key.io import write_wav
from middle_key.parse_args import parse_args
from middle_key.radio import RadioSettings, RadioType, create_sdr
from middle_key.radio.constants import RADIO_OFFSET_HZ


def build_burst_filename(burst: Burst) -> str:
    """Build a burst's WAV filename from its UTC start time and channel frequency.

    Example: 20261102T142217.123Z_119800k.wav (2026-11-02 14:22:17.123 UTC on 119.800 MHz).
    Names sort chronologically, and the milliseconds keep two bursts that start in the same
    second from overwriting each other.

    Args:
        burst: The burst to name.

    Returns:
        The filename, without a directory.
    """
    # LOCAL VARIABLES
    start = burst.start_time  # UTC start time
    filename = ""             # Return value

    # BUILD IT
    filename = (f"{start:%Y%m%dT%H%M%S}.{start.microsecond // 1000:03d}Z_"
                f"{burst.channel_freq / 1e3:.0f}k.wav")

    # DONE
    return filename


def print_meter(monitor: ChannelMonitor) -> None:
    """Overwrite the current console line with a channel's power and squelch status.

    Args:
        monitor: The channel's ChannelMonitor, after at least one process_chunk() call.
    """
    # LOCAL VARIABLES
    detector = monitor.detector                          # Squelch status source
    status = "OPEN  " if detector.is_open else "closed"  # Squelch state label
    floor = "warming up"                                 # Noise floor text

    # PRINT IT
    if detector.floor_db is not None:
        floor = (f"floor {detector.floor_db:6.1f} dBFS "
                 f"({monitor.power_db - detector.floor_db:+5.1f} dB)")
    print(f"\rChannel power {monitor.power_db:6.1f} dBFS, {floor}  [{status}]", end="",
          flush=True)


def save_burst(burst: Burst, out_dir: Path) -> Path:
    """Demodulate a burst, normalize its audio, and write it as a WAV file in out_dir.

    Args:
        burst: One complete transmission.
        out_dir: The directory to write the WAV file in (see build_burst_filename()).

    Returns:
        The path of the WAV file written.
    """
    # LOCAL VARIABLES
    audio = extract_normal_audio(burst.samples, burst.sample_rate)  # Normalized voice audio
    wav_path = out_dir / build_burst_filename(burst)                # Return value

    # WRITE IT
    write_wav(filename=wav_path, audio=audio, sample_rate=burst.sample_rate)

    # DONE
    return wav_path


def main() -> int:
    """Listen to one channel and save each transmission as its own WAV file, until Ctrl+C.

    Returns:
        EXIT_SUCCESS, or EXIT_FAILURE if the radio couldn't be opened or failed while streaming.
    """
    # LOCAL VARIABLES
    exit_code = EXIT_SUCCESS                # Return value
    args = parse_args()                     # CLI args
    debug = getattr(args, CLI_DEBUG)        # Debug mode?
    channel_freq = getattr(args, CLI_FREQ)  # Channel to listen to, Hz
    out_dir = Path(getattr(args, CLI_OUT))  # Where to save the WAV files
    monitor = None                          # Channel pipeline: complete transmissions out
    wav_path = None                         # Where the latest burst was saved

    # SETUP
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING,
                        format="%(levelname)s: %(message)s")

    # LISTEN
    try:
        with create_sdr(RadioSettings(center_freq=channel_freq - RADIO_OFFSET_HZ,
                                      gain=getattr(args, CLI_GAIN),
                                      radio_type=RadioType(getattr(args, CLI_RADIO)),
                                      freq_correction_ppm=getattr(args, CLI_PPM))) as sdr:
            print(f"Listening on {channel_freq / 1e6:.3f} MHz: SDR tuned to "
                  f"{sdr.actual_settings.center_freq / 1e6:.3f} MHz at "
                  f"{sdr.actual_settings.sample_rate:.0f} S/s, "
                  f"gain {sdr.actual_settings.gain:.1f} dB (Ctrl+C to stop)")
            monitor = ChannelMonitor(channel_freq=channel_freq, sdr_settings=sdr.actual_settings)
            print(f"Channel: {monitor.channelizer.offset_hz / 1e3:+.3f} kHz from center, "
                  f"decimated by {monitor.channelizer.decimation} to "
                  f"{monitor.channelizer.channel_rate:.0f} S/s.  Saving transmissions to {out_dir}")
            for chunk in sdr.stream_samples():
                for burst in monitor.process_chunk(chunk):
                    wav_path = save_burst(burst, out_dir)
                    print(f"\r{burst.start_time:%H:%M:%S}Z  {burst.channel_freq / 1e6:.3f} MHz  "
                          f"{burst.calculate_duration():5.1f} s  -> {wav_path}" + " " * 10)
                if debug:
                    print_meter(monitor)
    except KeyboardInterrupt:
        print("\nStopped (a transmission in progress, if any, was not saved)")
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as err:
        exit_code = EXIT_FAILURE
        print(f"\n{repr(err)}")
        if debug:
            raise err

    # DONE
    return exit_code
