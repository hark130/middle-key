"""Entry point for the Middle Key (MIKE) package."""


# Standard Imports
import sys
# Third Party Imports
# Local Imports
from middle_key.constants import EXIT_FAILURE, EXIT_SUCCESS
from middle_key.main import main


if __name__ == "__main__":
	exit_code = EXIT_FAILURE  # Exit code
	try:
		exit_code = main()
	except Exception as err:
		print(f"Unhandled exception: {repr(err)}")
		exit_code = EXIT_FAILURE
	finally:
		sys.exit(exit_code)
