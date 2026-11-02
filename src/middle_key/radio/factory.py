"""Create the right Sdr subclass for a RadioSettings: the radio sub-package's entry point.

To add a radio type:
    1. Add a member to RadioType (settings.py)
    2. Write an Sdr subclass in its own module (e.g., hackrf_sdr.py)
    3. Add a line to _SDR_CLASSES below
"""

# Standard Imports
from typing import Final
import importlib
# Third Party Imports
# Local Imports
from middle_key.radio.sdr import Sdr
from middle_key.radio.settings import RadioSettings, RadioType


# Where each RadioType's Sdr subclass lives: (module, class name).  Each module is only imported
# when its radio type is used, so e.g. the USRP's uhd package isn't needed to run a HackRF.
_SDR_CLASSES: Final[dict[RadioType, tuple[str, str]]] = {
    RadioType.USRP: ('middle_key.radio.usrp_sdr', 'UsrpSdr'),
}


def create_sdr(settings: RadioSettings) -> Sdr:
    """Create, but don't open, the Sdr for settings.radio_type.

    Args:
        settings: The requested radio configuration.

    Returns:
        An unopened Sdr subclass instance.  Use it in a with statement, or call open().

    Raises:
        ImportError: The radio's driver package (e.g., uhd) isn't installed.
        NotImplementedError: settings.radio_type has no Sdr subclass yet.
    """
    # LOCAL VARIABLES
    module_name = ''  # Module containing the Sdr subclass
    class_name = ''   # Name of the Sdr subclass
    sdr = None        # Return value

    # LOOK IT UP
    if settings.radio_type not in _SDR_CLASSES:
        raise NotImplementedError(f'Radio type {settings.radio_type} is not supported yet')
    module_name, class_name = _SDR_CLASSES[settings.radio_type]

    # CREATE IT
    sdr = getattr(importlib.import_module(module_name), class_name)(settings)

    # DONE
    return sdr
