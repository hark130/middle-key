"""Defines the SigMFMeta class.

Open, parse, and answer questions about a sigmf-meta file.
"""

# Standard Imports
from pathlib import Path
from typing import Any
# Third Party Imports
import numpy
import sigmf
# Local Imports
from middle_key.sigmfdtypeinfo import SigMFDTypeInfo
from middle_key.validation import validate_int, validate_path, validate_string


class SigMFMetaParser:
    """Answer questions about a sigmf-meta file."""

    # CORE CLASS METHODS
    # Methods listed in call order
    def __init__(self, meta_filename: Path) -> None:
        """SigMFMeta ctor."""
        self._meta_data = None           # The sigmf-meta data
        self._meta_file = meta_filename  # The sigmf-meta file

    # COMMON-USE METHODS
    def get_annotations_key(self, key: str) -> Any:
        """Fetch a key from sigmf.SigMFFile.ANNOTATION_KEY.

        Raises:
            FileNotFoundError: The meta data file is not found.
            KeyError: The object name is invalid or there's a mismatch between obj_name and key.
            TypeError: Bad data type.
            ValueError: Invalid value.
        """
        return self.get_obj_name_key_value(obj_name=sigmf.SigMFFile.ANNOTATION_KEY, key=key)

    def get_captures_key(self, key: str, index: int = 0) -> Any:
        """Fetch a key from a sigmf.SigMFFile.CAPTURE_KEY index.

        Raises:
            FileNotFoundError: The meta data file is not found.
            KeyError: The object name is invalid or there's a mismatch between obj_name and key.
            TypeError: Bad data type.
            ValueError: Invalid value.
        """
        return self.get_obj_name_key_value(obj_name=sigmf.SigMFFile.CAPTURE_KEY, key=key,
                                           index=index)

    def get_global_key(self, key: str) -> Any:
        """Fetch a key from sigmf.SigMFFile.GLOBAL_KEY.

        Raises:
            FileNotFoundError: The meta data file is not found.
            KeyError: The object name is invalid or there's a mismatch between obj_name and key.
            TypeError: Bad data type.
            ValueError: Invalid value.
        """
        return self.get_obj_name_key_value(obj_name=sigmf.SigMFFile.GLOBAL_KEY, key=key)

    def load_data(self) -> None:
        """Validate the meta file and load the data (if it hasn't been done already).

        Raises:
            FileNotFoundError: The meta data file is not found.
            TypeError: The meta_filename argument was not a Path object.
        """
        if self._meta_data is None:
            self._validate_file()
            self._load_file()

    # DATA-SPECIFIC METHODS
    # Methods listed in alphabetical order
    def determine_freq_range(self, index: int = 0) -> tuple[float, float]:
        """Determine the minimum and maximum frequencies from the capture at the specified index.

        Attempt to fetch the optional values from the meta data.  Failing that, calculate the
        range based on the sample rate and center frequency.
        See: https://sigmf.readthedocs.io/en/latest/advanced.html

        Args:
            index: [OPTIONAL] The index, from the list of captures, to fetch the frequency from.

        Returns:
            A tuple of the frequency edges: (low, high).

        Raises:
            SyntaxError: A mismatch of sigmf.SigMFFile.FLO_KEY and sigmf.SigMFFile.FHI_KEY keys.
                The SigMF Specification Version v1.2.5 states: "It is REQUIRED that both
                freq_lower_edge and freq_upper_edge be provided, or neither; the use of just one
                field is not allowed."
        """
        # LOCAL VARIABLES
        low_freq = self.get_freq_low(index=index)    # Minimum frequency
        high_freq = self.get_freq_high(index=index)  # Maximum frequency
        freq_range = None                            # Tuple of low and high freq values

        # VALIDATION
        # Meta data didn't specify the range so we'll calculate it
        if low_freq is None and high_freq is None:
            freq_range = self._calculate_freq_range(index=index)
        elif low_freq is not None and high_freq is not None:
            freq_range = tuple((low_freq, high_freq))
        else:
            raise SyntaxError(f'Either both {sigmf.SigMFFile.FLO_KEY} and '
                              f'{sigmf.SigMFFile.FHI_KEY} be provided, or neither')

        # DONE
        return freq_range

    def get_bandwidth(self) -> int:
        """Fetch the global sample rate as the estimated bandwidth of the capture.

        See: https://sigmf.readthedocs.io/en/latest/advanced.html

        Returns:
            The estimated bandwidth of the capture.
        """
        return self.get_sample_rate()

    def get_center_freq(self, index: int = 0) -> int:
        """Fetch the center frequency of the capture at the specified index.

        Args:
            index: [OPTIONAL] The index, from the list of captures, to fetch the frequency from.

        Returns:
            The center frequency from the capture at index 0.
        """
        return self.get_captures_key(key=sigmf.SigMFFile.FREQUENCY_KEY, index=index)

    def get_datatype(self) -> numpy.dtype:
        """Translate the SigMF datatype metadata into a numpy.dtype data type.

        Parse the global core:datatype key into a numpy.dtype type for the purposes of positively
        determining the data type.

        Returns:
            A numpy.dtype object based on the metadata's datatype field.

        Raises:
            FileNotFoundError: The meta data file is not found.
            KeyError: The object name is invalid or there's a mismatch between obj_name and key.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Invalid value.
        """
        # LOCAL VARIBLES
        np_dtype = None                       # The numpy dtype
        smfdtypinfo = self._get_dtype_info()  # SigMFDTypeInfo obj

        # GET IT
        if smfdtypinfo is not None:
            np_dtype = smfdtypinfo.get_dtype

        # DONE
        return np_dtype

    def get_freq_high(self, index: int = 0) -> float:
        """Fetch the maximum available frequency of the capture.

        Args:
            index: [OPTIONAL] The index, from the list of captures, to fetch the values from.
        """
        # LOCAL VARIABLES
        high_freq = None  # Upper edge frequency

        # GET IT
        try:
            high_freq = self.get_captures_key(key=sigmf.SigMFFile.FHI_KEY, index=index)
        except KeyError:
            pass  # The key is optional

        # DONE
        return high_freq

    def get_freq_low(self, index: int = 0) -> float:
        """Fetch the minimum available frequency of the capture.

        Args:
            index: [OPTIONAL] The index, from the list of captures, to fetch the values from.
        """
        # LOCAL VARIABLES
        low_freq = None  # Lower edge frequency

        # GET IT
        try:
            low_freq = self.get_captures_key(key=sigmf.SigMFFile.FLO_KEY, index=index)
        except KeyError:
            pass  # The key is optional

        # DONE
        return low_freq

    def get_obj_name_key_value(self, obj_name: str, key: str, index: int = 0) -> Any:
        """Fetch a key value from a SigMF metadata object.

        See https://sigmf.org/ for more information on the SigMF metadata objects.

        Args:
            obj_name: The name of the SigMF metadata object to search.  Use sigmf.SigMFFile macros
                for this argument (e.g., GLOBAL_KEY, CAPTURE_KEY, ANNOTATION_KEY).
                See sigmf.SigMFFile.VALID_KEYS.keys() for a list of actual values.
            key: The key to fetch from the specified obj_name.  Use sigmf.SigMFFile macros
                for this argument.
            index: [OPTIONAL] The index, from the list of captures, to fetch the values from.

        Returns:
            The value found at obj_name:key.
        """
        # LOCAL VARIABLES
        value = None  # The value from obj_name:key

        # SETUP
        self.load_data()

        # GET IT
        value = self._get_obj_name_key_value(obj_name=obj_name, key=key, index=index)

        # DONE
        return value

    def get_read_datatype(self) -> numpy.dtype:
        """Determine numpy.dtype data type necessary to read the SigMF file.

        Parse the global core:datatype key into a numpy.dtype type for the purposes of reading
        the data file contents.  There is no guarantee that the dataype necessary to read the
        data is the same as the actual data type.  The return value will reflect the byteorder
        of the data.

        Returns:
            A numpy.dtype data type to read the data file contents as.

        Raises:
            FileNotFoundError: The meta data file is not found.
            KeyError: The object name is invalid or there's a mismatch between obj_name and key.
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Invalid value.
        """
        # LOCAL VARIBLES
        np_dtype = None                       # The numpy dtype
        smfdtypinfo = self._get_dtype_info()  # SigMFDTypeInfo obj

        # GET IT
        if smfdtypinfo is not None:
            np_dtype = smfdtypinfo.read_dtype

        # DONE
        return np_dtype

    def get_sample_rate(self) -> int:
        """Fetch the global sample rate from the capture.

        Returns:
            The global sample rate of the capture.
        """
        return self.get_global_key(key=sigmf.SigMFFile.SAMPLE_RATE_KEY)

    # CLASS HELPER METHODS
    # Methods listed in alphabetical order
    def _calculate_freq_range(self, index: int = 0) -> tuple[float, float]:
        """Calculate the low and high frequency values.

        From https://sigmf.readthedocs.io/en/latest/advanced.html

        low_freq = center_freq - 0.5*sample_rate
        high_freq = center_freq + 0.5*sample_rate

        Args:
            index: [OPTIONAL] The index, from the list of captures, to fetch the values from.

        Returns:
            A tuple of the frequency edges: (low, high) calculated from the center frequency
            and sample rate.
        """
        # LOCAL VARIABLES
        sample_rate = self.get_sample_rate()                  # Sample rate
        center_freq = self.get_center_freq(index=index)       # Center frequency
        low_freq = float(center_freq - (0.5 * sample_rate))   # Lower edge frequency
        high_freq = float(center_freq + (0.5 * sample_rate))  # Upper edge frequency

        # DONE
        return tuple((low_freq, high_freq))

    def _get_base_filename(self) -> str:
        """Dynamically fetch the base meta filename.

        Raises:
            FileNotFoundError: The meta data file is not found.
            TypeError: The meta_filename argument was not a Path object.
        """
        # LOCAL VARIABLES
        base_name = None  # The base filename, sans file extension, of self._meta_file

        # VALIDATION
        self._validate_file()

        # PARSE IT
        base_name = self._meta_file.with_suffix('')

        # DONE
        return base_name

    def _get_dtype_info(self) -> SigMFDTypeInfo:
        """Construct a SigMFDTypeInfo object using the global DATATYPE_KEY.

        Returns:
            A validated SigMFDTypeInfo object constructed from the global DATATYPE_KEY.

        Raises:
            RuntimeError: A SigMF-specific exception was raised (see: help(sigmf.error) for details)
            TypeError: Bad data type.
            ValueError: Bad value.
        """
        # LOCAL VARIBLES
        datatype_val = self.get_global_key(key=sigmf.SigMFFile.DATATYPE_KEY)  # core:datatype
        smfdtypinfo = None                                                    # SigMFDTypeInfo obj

        # GET IT
        if datatype_val is not None:
            smfdtypinfo = SigMFDTypeInfo(datatype_val)
            smfdtypinfo.validate_content()  # Validate the format sooner rather than later

        # DONE
        return smfdtypinfo

    def _get_obj_name_key_value(self, obj_name: str, key: str, index: int = 0) -> Any:
        """Fetch a key value from a SigMF metadata object.

        This method does not validate the data has been loaded.  Call self.load_data() first.

        Args:
            obj_name: The name of the SigMF metadata object to search.  Use sigmf.SigMFFile macros
                for this argument (e.g., GLOBAL_KEY, CAPTURE_KEY, ANNOTATION_KEY).
                See sigmf.SigMFFile.VALID_KEYS.keys() for a list of actual values.
            key: The key to fetch from the specified obj_name.  Use sigmf.SigMFFile macros
                for this argument.
            index: [Optional] Only used for obj_names that contain lists (e.g., captures)

        Returns:
            The value on success, None on any IndexError/KeyError exceptions.
        """
        # LOCAL VARIABLES
        key_val = None  # Key value from the obj_name dictionary

        # INPUT VALIDATION
        # obj_name && key
        self._validate_obj_name_key_pair(obj_name=obj_name, key=key)
        # index
        validate_int(index, 'index')
        if index < 0:
            raise TypeError(f'The "index" value is invalid: {index}')

        # GET VALUE
        match obj_name:
            # global
            case sigmf.SigMFFile.GLOBAL_KEY:
                key_val = self._meta_data.get_global_field(key)
            # captures
            case sigmf.SigMFFile.CAPTURE_KEY:
                cap_list = self._meta_data.get_captures()
                try:
                    key_val = cap_list[index][key]
                except (IndexError, KeyError):
                    pass  # Ignore these Exceptions and return None instead
            # annotations
            case sigmf.SigMFFile.ANNOTATION_KEY:
                key_val = self._meta_data.get_annotations(key)
            case _:
                raise NotImplementedError(f'Object "{obj_name}" passed validation '
                                          'but is not supported')

        # DONE
        return key_val

    def _load_file(self) -> None:
        """Load the meta filename.

        This method does not validate any attributes.  Call self._validate_file() first.
        """
        self._meta_data = sigmf.sigmffile.fromfile(self._get_base_filename())

    def _validate_obj_name_key_pair(self, obj_name: str, key: str) -> None:
        """Validates a SigMF metadata object name against a key.

        Raises:
            KeyError: The obj_name name is invalid or there's a mismatch between obj_name and key.
        """
        # INPUT VALIDATION
        # Object
        self._validate_obj_name_name(obj_name=obj_name)
        # Key
        validate_string(validate_this=key, param_name='key', can_be_empty=False)

    def _validate_obj_name_name(self, obj_name: str) -> None:
        """Validates a SigMF metadata object name.

        Raises:
            KeyError: The obj_name name is invalid.
            TypeError: Bad data type.
            ValueError: Invalid value.
        """
        # INPUT VALIDATION
        validate_string(validate_this=obj_name, param_name='obj_name', can_be_empty=False)
        if obj_name not in sigmf.SigMFFile.VALID_KEYS:
            raise KeyError(f'The obj_name name "{obj_name}" is not a valid SigMF key')

    def _validate_file(self) -> None:
        """Validate the meta filename.

        Raises:
            FileNotFoundError: The meta data file is not found.
            TypeError: The meta_filename argument was not a Path object.
            ValueError: Invalid value.
        """
        validate_path(validate_this=self._meta_file, param_name='meta_filename', must_exist=True)
