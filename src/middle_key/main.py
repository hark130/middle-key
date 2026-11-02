"""Executes Middle Key (MIKE)."""


# Standard Imports
# Third Party Imports
# Local Imports
from middle_key.constants import (CLI_DEBUG, CLI_DEBUG_DEFAULT, CLI_FREQ, CLI_GAIN, CLI_OUT,
                                  EXIT_FAILURE, EXIT_SUCCESS)
from middle_key.parse_args import parse_args


def main() -> int:
    """do_it()."""
    try:
        exit_code = EXIT_SUCCESS        # Return value
        debug_mode = CLI_DEBUG_DEFAULT  # Debug mode?
        args = parse_args()             # CLI args
    except (OSError, RuntimeError, TypeError, ValueError) as err:
        exit_code = EXIT_FAILURE
        print(repr(err))
        if debug_mode:
            raise err

    # DONE
    return exit_code
