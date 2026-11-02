"""Defines the SigMFDTypeInfo() dataclass to answer questions about SigMF Dataset Format values.

USAGE:
    from middle_key.sigmfdtypeinfo import Endian, SigMFDTypeInfo

    sdf_val1 = SigMFDTypeInfo('cf32_le')
    sdf_val1.is_complex  # True
    sdf_val1.get_dtype   # dtype('float32')
    sdf_val1.is_signed   # True
    sdf_val1.get_endian  # Endian.LITTLE

    sdf_val2 = SigMFDTypeInfo('ru8')
    sdf_val2.is_complex  # False
    sdf_val2.get_dtype   # dtype('uint8')
    sdf_val2.is_signed   # False
    sdf_val2.get_endian  # Endian.UNSPECIFIED
"""

# Standard Imports
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final
import sys
# Third Party Imports
from sigmf import sigmffile
from sigmf.error import SigMFError
import numpy
# Local Imports
from middle_key.validation import validate_bool, validate_string, validate_type


# SigMF dtype_info dictionary keys
_SIG_DINFO_KEY_COMP_DTYPE: Final[str] = 'component_dtype'
_SIG_DINFO_KEY_COMPLEX: Final[str] = 'is_complex'
_SIG_DINFO_KEY_MAP_TYPE: Final[str] = 'memmap_map_type'
_SIG_DINFO_KEY_SAMP_SIZE: Final[str] = 'sample_size'
_SIG_DINFO_KEY_UNSIGNED: Final[str] = 'is_unsigned'


class Endian(Enum):
    """Endianness."""
    UNSPECIFIED = 0  # Unknown endianness or not applicable
    BIG = 2          # Big-endian
    LITTLE = 1       # Little-endian


@dataclass()
class SigMFDTypeInfo():
    """Parse and answer questions about SigMF Dataset Format values.

    Utilizes sigmf.sigmffile.dtype_info() and then translates the dictionary values.

    Arguments:
        dataset: The SigMF Dataset Format value, as a string, to parse.
    """

    # Public Attributes
    dataset: str  # SigMF Dataset Format value

    # Private Attributes
    _dtype_dict: dict = None
    _validated: bool = field(default=False, repr=False)

    # CORE METHODS
    # In alphabetical order

    def validate_content(self) -> None:
        """Validate the contents of the dataclass: type, content, length, format, etc.

        Raises:
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        if self._validated is not True:
            validate_bool(self._validated, 'internal attribute _validated')
            validate_string(validate_this=self.dataset, param_name='dataset', can_be_empty=False)
            self._validate_dataset_format()
            self._validated = True

    # HUMAN-READABLE METHODS
    # In alphabetical order

    @property
    def bit_width(self) -> int:
        """Determines the dataset's bit width.

        Returns:
            An integer representing the bit width.

        Raises:
            KeyError: The necessary key was missing.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        self.validate_content()
        return self._get_bit_width()

    @property
    def get_dtype(self) -> numpy.dtype:
        """Determines the dataset's component data type.

        Returns:
            A numpy.dtype object.

        Raises:
            KeyError: The necessary key was missing.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        self.validate_content()
        return numpy.dtype(_get_safe_key(self._dtype_dict, _SIG_DINFO_KEY_COMP_DTYPE, silent=False))

    @property
    def get_endian(self) -> Endian:
        """Determine the endianness of the dataset.

        Returns:
            An Endian object indicating the endianness.

        Raises:
            KeyError: The necessary key was missing.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
                or there's an internal disagreement as to the endianness.
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        self.validate_content()
        map_type = _determine_endianness(_get_safe_key(self._dtype_dict, _SIG_DINFO_KEY_MAP_TYPE,
                                                       silent=True))
        byte_order = self._read_byteorder()
        if map_type != byte_order:
            raise RuntimeError(f'Endianness disagreement: The dtype_info[{_SIG_DINFO_KEY_MAP_TYPE}]'
                               f' suggests {repr(map_type)} while the numpy.dtype().byteorder '
                               f'suggests {repr(byte_order)}')
        return byte_order

    @property
    def is_complex(self) -> bool:
        """Determines if dataset is complex or real.

        Returns:
            True if complex.  False if it's real.

        Raises:
            KeyError: The necessary key was missing.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        self.validate_content()
        return _get_safe_key(self._dtype_dict, _SIG_DINFO_KEY_COMPLEX, silent=False)

    @property
    def is_signed(self) -> bool:
        """Determines if dataset is signed or unsigned.

        Returns:
            True if signed.  False if it's unsigned.

        Raises:
            KeyError: The necessary key was missing.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        self.validate_content()
        return not _get_safe_key(self._dtype_dict, _SIG_DINFO_KEY_UNSIGNED, silent=False)

    @property
    def read_dtype(self) -> numpy.dtype:
        """Determine the data type to read samples of this dataset (see: numpy.fromfile()).

        This value is separate, but related to get_dtype in that complex values are made up
        of two components (I & Q) instead of one.

        Returns:
            A numpy.dtype object.

        Raises:
            KeyError: The necessary key was missing.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        self.validate_content()
        return self._read_dtype()

    # PRIVATE METHODS
    # In alphabetical order

    def _get_bit_width(self) -> int:
        """Parse the bit width from the dtype dictionary.

        The sample_size dictionary is queried and adjusted if the dtype is complex.
        """
        num_components = 1  # The num of components for a given data type: 1 for real, 2 for complex
        bit_width = None    # Bit width
        # Sample size represents the total size of all sample components
        samp_size = _get_safe_key(self._dtype_dict, _SIG_DINFO_KEY_SAMP_SIZE, silent=False)
        if self.is_complex:
            num_components = 2  # The bit width is doubled for complex samples b/c I & Q are read
        bit_width = samp_size * int(8 / num_components)
        return bit_width

    def _read_byteorder(self) -> Endian:
        """Use the numpy.dtype().byteorder attribute to determine the endianness."""
        return _determine_endianness(self.get_dtype.byteorder)

    def _read_dtype(self) -> numpy.dtype:
        """Determine the data type to read samples of this dataset."""
        # LOCAL VARIABLES
        data_type = None  # The data type to use for reading samples of this dataset
        # Component dtype
        comp_dtype = numpy.dtype(_get_safe_key(self._dtype_dict, _SIG_DINFO_KEY_COMP_DTYPE,
                                 silent=False))

        # TRANSLATE DTYPE
        if self.is_complex and numpy.issubdtype(comp_dtype, numpy.floating):
            # Convert complex float -> numpy complex dtype
            if comp_dtype in (numpy.dtype(numpy.float32), numpy.dtype('>f4')):
                data_type = numpy.dtype(numpy.complex64)
            elif comp_dtype in (numpy.dtype(numpy.float64), numpy.dtype('>f8')):
                data_type = numpy.dtype(numpy.complex128)
            else:
                raise ValueError(f'Unsupported float width for complex dtype: {comp_dtype}')
            # Preserve endianness
            if self.get_endian == Endian.BIG:
                data_type = data_type.newbyteorder('>')
        else:
            # All others
            data_type = comp_dtype

        # DONE
        return data_type

    def _validate_dataset_format(self) -> None:
        """Validate the content of self.dataset utilizing sigmf and store the dictionary."""
        try:
            self._dtype_dict = sigmffile.dtype_info(self.dataset)
        except SigMFError as err:
            raise RuntimeError(f'The "dataset" value "{self.dataset}" failed SigMF validation '
                               f'with a bespoke Exception: {err}') from err
        except TypeError as err:
            raise TypeError(f'The "dataset" value "{self.dataset}" failed SigMF'
                            f'type validation: {err}') from err
        except ValueError as err:
            raise ValueError(f'The "dataset" value "{self.dataset}" failed '
                             f'basic SigMF validation: {err}') from err
        validate_type(self._dtype_dict, 'internal attribute _dtype_dict', dict)


def _determine_endianness(map_type) -> Endian:
    """Determine a SigMF data type's endianness.

    This function is intended to infer the endianness from the
    _SIG_DINFO_KEY_MAP_TYPE key's value in the dictionary returned by sigmf.sigmffile.dtype_info().

    NOTE: numpy.dtype().byteorder indicates the byte-order of a data-type object:
       '='  native
       '<'  little-endian
       '>'  big-endian
       '|'  not applicable

    Returns:
        An Endian value indicating what was found.  Endian.UNSPECIFIED is used for all errors,
        exceptions, and (most?) 8-bit values.

    Raises:
        None.  All raises are translated into Endian.UNSPECIFIED instead.
    """
    # LOCAL VARIABLES
    endianness = Endian.UNSPECIFIED  # The result

    # DETERMINE IT
    try:
        validate_string(map_type, 'map_type', can_be_empty=False)
    except (TypeError, ValueError):
        pass
    else:
        if map_type.startswith('<'):
            endianness = Endian.LITTLE
        elif map_type.startswith('>'):
            endianness = Endian.BIG
        elif map_type.startswith('='):
            endianness = _determine_native_endianness()

    # DONE
    return endianness


def _determine_native_endianness() -> Endian:
    """Determine the native endianness."""
    # LOCAL VARIABLES
    endianness = sys.byteorder       # The native endianness
    endian_obj = Endian.UNSPECIFIED  # Sys result tranlated into an Endian IntEnum object

    # RESULT VALIDATION
    validate_string(endianness, 'sys.byteorder', can_be_empty=False)
    endianness = endianness.lower()

    # DETERMINE IT
    if endianness == 'little':
        endian_obj = Endian.LITTLE
    elif endianness == 'big':
        endian_obj = Endian.BIG

    # DONE
    return endian_obj


# Leave me be, Pylint
# pylint: disable=broad-exception-caught
def _get_safe_key(dictionary: dict, key: Any, silent: bool = True) -> Any:
    """Safely get a key's value from a dictionary.

    Returns:
        Key value on success, None on any Exception.
    """
    # LOCAL VARIABLES
    value = None  # The key's value

    # INPUT VALIDATION
    validate_bool(silent, 'silent')

    # GET IT
    try:
        value = dictionary[key]
    except Exception as err:
        if not silent:
            raise err from err

    # DONE
    return value
# pylint: enable=broad-exception-caught
