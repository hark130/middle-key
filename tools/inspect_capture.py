"""Inspect a SigMF capture."""

# Standard Imports
from pathlib import Path
from typing import Final
import argparse
# Third Party Imports
from matplotlib.axes import Axes
from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
# Local Imports
from middle_key.constants import SIGMF_META_FILE_EXT
from middle_key.demod import demod_am
from middle_key.dsp import (convert_samples_to_db, convert_power_to_db, extract_normal_audio)
from middle_key.io import read_samples, write_wav
from middle_key.sigmfmetaparser import SigMFMetaParser


# CLI Arguments
CLI_ARG_CAPTURE: Final[str] = 'capture'  # Capture filename
CLI_ARG_DEBUG: Final[str] = 'debug'      # Debug logging
CLI_ARG_WAV: Final[str] = 'wav'          # Output WAV filename
# Plot settings
PLOT_MAX_POINTS: Final[int] = 4000   # Max points in the power-vs-time plot (screen resolution)
PLOT_NFFT: Final[int] = 4096         # FFT size for the spectrum: 48 kS/s / 4096 = ~12 Hz bins
PLOT_SPEC_NFFT: Final[int] = 1024    # FFT size for each spectrogram column: ~47 Hz bins, ~21 ms
PLOT_SPEC_RANGE_DB: Final[int] = 80  # Spectrogram colors span this many dB below the peak


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    # LOCAL VARIABLES
    parser = argparse.ArgumentParser(prog="inspect capture",
                                     description="Inspect a SigMF capture files.")
    args = None  # Parsed arguments

    # DEFINE THEM
    parser.add_argument(f"-{CLI_ARG_CAPTURE[0]}", f"--{CLI_ARG_CAPTURE}", required=True,
                        action='store', help="Base filename for the SigMF data and meta file")
    parser.add_argument(f"-{CLI_ARG_DEBUG[0]}", f"--{CLI_ARG_DEBUG}", action="store_true",
                        help="Verbose logging", required=False)
    parser.add_argument(f"-{CLI_ARG_WAV[0]}", f"--{CLI_ARG_WAV}", required=False, default=None,
                        action='store', metavar='WAV_FILE',
                        help="Also demodulate the capture and write the audio to this WAV file")

    # PARSE THEM
    args = parser.parse_args()

    # DONE
    return args


def plot_it(samples: np.ndarray, sample_rate: float, center_freq: float, filename: str) -> None:
    """Plot samples."""
    # LOCAL VARIABLES
    figure = None  # Figure holding all plots
    axes = None    # One Axes per plot

    # PLOT IT
    figure, axes = plt.subplots(3, 1, figsize=(12, 10))
    plot_power(axes[0], samples, sample_rate)
    plot_spectrum(axes[1], samples, sample_rate, center_freq)
    plot_spectrogram(axes[2], samples, sample_rate, center_freq)
    figure.suptitle(Path(filename).name)
    figure.tight_layout()
    plt.show()


def plot_power(axes: Axes, samples: np.ndarray, sample_rate: float) -> None:
    """Plot power (dBFS) against time, showing the peak of each block so short bursts survive.

    Plotting every sample of a long capture is slow and unreadable, so the samples are split into
    at most PLOT_MAX_POINTS blocks and each block's peak is plotted.  Peaks (not every Nth
    sample) guarantee a short transmission can't fall between the plotted points.

    Args:
        axes: The matplotlib Axes to draw on.
        samples: Complex baseband samples.
        sample_rate: The sample rate in samples per second.
    """
    # LOCAL VARIABLES
    block_len = max(1, len(samples) // PLOT_MAX_POINTS)  # Samples per plotted point
    num_blocks = len(samples) // block_len               # Number of plotted points
    blocks = None                                        # Shape (num_blocks, block_len)
    peaks_db = None                                      # Peak power of each block, dBFS
    times = None                                         # Start time of each block, seconds

    # COMPUTE IT
    blocks = samples[:num_blocks * block_len].reshape(num_blocks, block_len)
    peaks_db = convert_samples_to_db(np.max(np.abs(blocks), axis=1))
    times = np.arange(num_blocks) * block_len / sample_rate

    # PLOT IT
    axes.plot(times, peaks_db, linewidth=0.8)
    axes.set_title("Power vs. time (peak per block)")
    axes.set_xlabel("Time (s)")
    axes.set_ylabel("Power (dBFS)")
    axes.grid(True, alpha=0.3)


def plot_spectrum(axes: Axes, samples: np.ndarray, sample_rate: float,
                  center_freq: float) -> None:
    """Plot the averaged power spectral density (Welch's method) in absolute RF frequency.

    Args:
        axes: The matplotlib Axes to draw on.
        samples: Complex baseband samples.
        sample_rate: The sample rate in samples per second.
        center_freq: The RF frequency, in Hz, that 0 Hz in the samples corresponds to.
    """
    # LOCAL VARIABLES
    freqs = None  # Frequency of each bin, Hz relative to center_freq
    psd = None    # Power spectral density of each bin, full scale^2/Hz

    # COMPUTE IT
    freqs, psd = signal.welch(samples, fs=sample_rate, nperseg=min(PLOT_NFFT, len(samples)),
                              return_onesided=False)
    freqs = np.fft.fftshift(freqs)
    psd = np.fft.fftshift(psd)

    # PLOT IT
    axes.plot((center_freq + freqs) / 1e6, convert_power_to_db(psd), linewidth=0.8)
    axes.set_title("Averaged spectrum")
    axes.set_xlabel("Frequency (MHz)")
    axes.set_ylabel("PSD (dBFS/Hz)")
    axes.ticklabel_format(axis="x", useOffset=False)
    axes.grid(True, alpha=0.3)


def plot_spectrogram(axes: Axes, samples: np.ndarray, sample_rate: float,
                     center_freq: float) -> None:
    """Plot a spectrogram (waterfall): frequency against time, with color showing power.

    Uses non-overlapping segments to keep memory reasonable on long captures.  The colors span
    PLOT_SPEC_RANGE_DB below the strongest bin, like an SDR waterfall, so a few near-zero bins
    can't stretch the color scale and wash out everything else.

    Args:
        axes: The matplotlib Axes to draw on.
        samples: Complex baseband samples.
        sample_rate: The sample rate in samples per second.
        center_freq: The RF frequency, in Hz, that 0 Hz in the samples corresponds to.
    """
    # LOCAL VARIABLES
    nfft = min(PLOT_SPEC_NFFT, len(samples))  # Samples per spectrogram column
    freqs = None                              # Frequency of each row, Hz relative to center_freq
    times = None                              # Center time of each column, seconds
    sxx = None                                # Power spectral density, (rows, columns)
    sxx_db = None                             # sxx in dB
    image = None                              # The drawn image, needed for the colorbar

    # COMPUTE IT
    freqs, times, sxx = signal.spectrogram(samples, fs=sample_rate, nperseg=nfft, noverlap=0,
                                           return_onesided=False)
    freqs = np.fft.fftshift(freqs)
    sxx_db = convert_power_to_db(np.fft.fftshift(sxx, axes=0))

    # PLOT IT
    image = axes.imshow(sxx_db, aspect="auto", origin="lower",
                        vmin=sxx_db.max() - PLOT_SPEC_RANGE_DB, vmax=sxx_db.max(),
                        extent=(times[0], times[-1], (center_freq + freqs[0]) / 1e6,
                                (center_freq + freqs[-1]) / 1e6))
    axes.figure.colorbar(image, ax=axes, label="PSD (dBFS/Hz)")
    axes.set_title("Spectrogram")
    axes.set_xlabel("Time (s)")
    axes.set_ylabel("Frequency (MHz)")
    axes.ticklabel_format(axis="y", useOffset=False)


def main():
    """Read a SigMF capture and plot it."""
    # LOCAL VARIABLES
    args = parse_args()                                                # Parsed CLI args
    debug = getattr(args, CLI_ARG_DEBUG)                               # Debug mode?
    wav_file = getattr(args, CLI_ARG_WAV)                              # Optional output file
    filename = getattr(args, CLI_ARG_CAPTURE)                          # Capture filename
    meta_path = Path(filename).with_suffix('.' + SIGMF_META_FILE_EXT)  # SigMF metadata filename
    meta = SigMFMetaParser(meta_filename=meta_path)                    # SigMF metadata
    sample_rate = meta.get_sample_rate()                               # Samples per second
    center_freq = meta.get_center_freq()                               # RF frequency of 0 Hz, Hz
    samples = read_samples(filename)                                   # Complex baseband samples
    audio = None                                                       # Real values per sample

    # SETUP
    if center_freq is None:
        center_freq = 0.0

    # SUMMARIZE IT
    if debug:
        print(f"FILENAME: {filename}")
        print(f"SAMPLES: {len(samples)} ({len(samples) / sample_rate:.1f} s at "
              f"{sample_rate} S/s, centered on {center_freq / 1e6} MHz)")

    # INSPECT IT
    if wav_file is not None:
        audio = extract_normal_audio(samples, sample_rate)
        write_wav(filename=wav_file, audio=audio, sample_rate=sample_rate)
        if debug:
            print(f"WAV: {wav_filename}")
    plot_it(samples=samples, sample_rate=sample_rate, center_freq=center_freq, filename=filename)


if __name__ == "__main__":
    main()
