"""Inspect a wav file."""

# Standard Imports
from typing import Final
# Third Party Imports
import numpy as np
from scipy.io import wavfile
# Local Imports

FILE01: Final[str] = "./data/middle_key_01_s48k_sat_twr.wav"
FILE02: Final[str] = "./data/middle_key_02_s48k_sat_twr2.wav"


def print_details(filename: str) -> None:
	"""Print details about a wav file."""
	rate, data = wavfile.read(filename)
	audio = data.astype(np.float64) / 32767
	print(f"\nFILENAME: {filename}")
	print(f"rate: {rate} Hz | dtype: {data.dtype} | samples: {len(data)} | "
		  f"duration: {len(data) / rate:.2f} s")
	print(f"peak: {np.abs(audio).max():.4f} FS | "
		  f"rms: {20 * np.log10(np.sqrt(np.mean(audio**2)) + 1e-12):.1f} dBFS")
	print(f"zeros: {np.mean(data == 0) * 100:.1f}% | unique values: {len(np.unique(data))}\n")


def main() -> None:
	"""do_it()."""
	files = [FILE01, FILE02]
	for file in files:
		print_details(filename=file)


if __name__ == "__main__":
	main()
