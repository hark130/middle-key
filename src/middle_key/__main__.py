"""Entry point for the Middle Key (MIKE) package."""


# Standard Imports
import sys
# Third Party Imports
# Local Imports
from middle_key.constants import EXIT_FAILURE, EXIT_SUCCESS
from middle_key.main import main


# pylint: disable=broad-exception-caught
if __name__ == "__main__":
    exit_code = EXIT_SUCCESS  # Exit code
    try:
        exit_code = main()
    except Exception as err:
        print(f"Unhandled exception: {repr(err)}")
        exit_code = EXIT_FAILURE
    finally:
        sys.exit(exit_code)
# pylint: enable=broad-exception-caught
