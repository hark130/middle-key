"""Define macro constants as a single point of truth."""

# Standard Imports
from getpass import getuser
from typing import Final
# Third Party Imports
from sigmf import SigMFFile
# Local Imports

# Assumed file extensions
SIGMF_DATA_FILE_EXT: Final[str] = 'sigmf-data'
SIGMF_META_FILE_EXT: Final[str] = 'sigmf-meta'
