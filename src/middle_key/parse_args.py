"""Parse the CLI arguments."""

# Standard Imports
import argparse
import os
# Third Party Imports
# Local Imports
from middle_key.constants import (CLI_DEBUG, CLI_FREQ, CLI_GAIN, CLI_GAIN_DEFAULT, CLI_OUT,
                                  CLI_OUT_DEFAULT)


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    # LOCAL VARIABLES
    parser = argparse.ArgumentParser(prog="Middle Key (MIKE)",
                                     description="Capture and save airband traffic")
    args = None   # Parsed arguments
    out_dir = ''  # CLI output directory

    # DEFINE THEM
    parser.add_argument(f"-{CLI_DEBUG[0]}", f"--{CLI_DEBUG}", default=False,
                        required=False, action="store_true", help="Verbose logging")
    parser.add_argument(f"-{CLI_FREQ[0]}", f"--{CLI_FREQ}", type=float, required=True,
                        help="Channel frequency in Hz")
    parser.add_argument(f"-{CLI_GAIN[0]}", f"--{CLI_GAIN}", type=float, default=CLI_GAIN_DEFAULT,
                        required=False, help="RF gain in dB")
    parser.add_argument(f"-{CLI_OUT[0]}", f"--{CLI_OUT}", type=str, default=CLI_OUT_DEFAULT,
                        required=False, help="Output directory for wav files")

    # PARSE AND VALIDATE THEM
    args = parser.parse_args()
    out_dir = getattr(args, CLI_OUT)
    if not os.path.isdir(out_dir):
        raise FileNotFoundError(f"Unable to locate the --{CLI_OUT} directory '{out_dir}'")

    # DONE
    return args
