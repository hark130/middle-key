"""Inspect a SigMF capture."""

# Standard Imports
from typing import Final
import argparse
# Third Party Imports
# Local Imports
from middle_key.io import read_samples


# CLI Arguments
CLI_ARG_CAPTURE: Final[str] = 'capture'  # Capture filename
CLI_ARG_DEBUG: Final[str] = 'debug'      # Debug logging


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    # LOCAL VARIABLES
    parser = argparse.ArgumentParser(prog="inspect capture",
                                     description="Inspect a SigMF capture files.")
    args = None  # Parsed arguments

    # DEFINE THEM
    parser.add_argument(f"-{CLI_ARG_CAPTURE[0]}", f"--{CLI_ARG_CAPTURE}", required=True,
                        action='store', help="Base filename for the SigMF data and meta file")
    parser.add_argument(f"--{CLI_ARG_DEBUG}", action="store_true", help="Verbose logging",
                        required=False)

    # PARSE THEM
    args = parser.parse_args()

    # DONE
    return args


def main():
    """do_it()."""
    args = parse_args()                        # Parsed CLI args
    debug = getattr(args, CLI_ARG_DEBUG)       # Debug mode?
    filename = getattr(args, CLI_ARG_CAPTURE)  # Capture filename
    print(f"FILENAME: {filename}")  # DEBUGGING
    samples = read_samples(filename)           # Read samples
    print(f"SAMPLES: {samples}")  # DEBUGGING


if __name__ == "__main__":
    main()
