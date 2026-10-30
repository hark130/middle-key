"""Read/write files."""

# Standard Imports
from pathlib import Path
# Third Party Imports
import numpy as np
# Local Imports
from middle_key.constants import SIGMF_DATA_FILE_EXT, SIGMF_META_FILE_EXT
from middle_key.sigmfmetaparser import SigMFMetaParser
from middle_key.validation import validate_bool, validate_path, validate_string


def read_samples(filename: str | Path) -> np.ndarray:
    """Read samples from an IQ file or SigMF dataset.

    Args:
        filename: The relative or absolute output file path to save the samples to.  If sigmf_data
            is True, the file extension of this filename will be changed to match the SigMF format.
    """
    # LOCAL VARIABLES
    file_path = filename  # The filename argument positively changed to be a Path object
    samples = None        # The array of samples read from filename

    # INPUT VALIDATION
    # filename
    if isinstance(filename, str):
        file_path = Path(filename)
    validate_path(file_path, "filename", must_exist=False)

    # READ IT
    samples = _read_sigmf_samples(basename=file_path.with_suffix(''))

    # DONE
    return samples


def _read_raw_samples(filename: Path, sample_dtype: np.dtype) -> np.ndarray:
    """Read a raw IQ file into an array.

    Args:
        filename: The relative or absolute output file path to save the samples to.
        sample_dtype: The data type of the samples to read.

    Returns:
        An array of the samples from filename.

    Raises:
        FileNotFoundError: filename is not found.
        OSError: filename exists but is not a file.
        TypeError: Bad data type.
        ValueError: Bad value.
    """
    # LOCAL VARIABLES
    samples = None  # The array of samples read from filename

    # INPUT VALIDATION
    _validate_read_raw_samples(filename=filename, sample_dtype=sample_dtype)

    # READ IT
    samples = np.fromfile(file=filename, dtype=sample_dtype)

    # DONE
    return samples


def _read_sigmf_samples(basename: Path) -> np.ndarray:
    """Read a SigMF dataset into an array.

    1. Read the SigMF metadata
    2. Convert the SIG_GLOB_DATATYPE_KEY value to a numpy.dtype object
    3. Read the data

    Args:
        basename: The base filename of the SigMF dataset.

    Raises:
        FileNotFoundError: filename is not found.
        OSError: The filename exists but filename is not a file.
        TypeError: Bad data type.
        ValueError: Bad value.
    """
    # LOCAL VARIABLES
    samples = None     # The samples read from basename.SIGMF_DATA_FILE_EXT
    data_path = None   # The SigMF data filename, derived from basename
    meta_path = None   # The SigMF metadata filename, derived from basename
    meta_data = None   # The SigMFMetaParser() object to parse SigMF metadata
    read_dtype = None  # The numpy.dtype type to read the samples as

    # INPUT VALIDATION
    data_path, meta_path = _validate_sigmf_paths(basename=basename)

    # READ IT
    # 1. Read the SigMF metadata
    meta_data = SigMFMetaParser(meta_filename=meta_path)
    # 2. Convert the SIG_GLOB_DATATYPE_KEY value to a numpy.dtype object
    read_dtype = meta_data.get_read_datatype()
    # 3. Read the data
    samples = _read_raw_samples(filename=data_path, sample_dtype=read_dtype)

    # DONE
    return samples


def _validate_dtype_like(dtlike: DTypeLike, param_name: str, must_be_complex: bool = True) -> None:
    """Validate a DTypeLike object on behalf of this module.

    Args:
        dtlike: The object to validate as a DTypeLike type.
        param_name: The name of the parameter to be used in exception messages.
        must_be_complex: [OPTIONAL] If true, verifies dtlike comforms to numpy.complex64
            or numpy.complex64 (after conversion to numpy.dtype()).

    Raises:
        TypeError: Bad data type.
        ValueError: Bad value.
    """
    # LOCAL VARIABLES
    test_dtlike = None  # The dtlike argument constructed as a numpy.dtype() object
    # Supported complex types (if must_be_complex is True)
    supp_complex = tuple((np.dtype('complex64'), np.dtype('complex128')))

    # INPUT VALIDATION
    validate_string(param_name, 'param_name', can_be_empty=True)
    validate_bool(must_be_complex, 'must_be_complex')
    try:
        test_dtlike = np.dtype(dtlike)
    except TypeError as err:
        raise TypeError(f'The "{param_name}" argument should have been a DTypeLike object '
                        f'but was "{type(dtlike)}" instead and rejected with {err}') from err
    except ValueError as err:
        raise ValueError(f'The "{param_name}" argument value of "{dtlike}" was rejected as a '
                         f'numpy.dtype() with "{err}" which indicates it is not compatible as '
                         'a DTypeLike object') from err
    if must_be_complex and test_dtlike not in supp_complex:
        raise ValueError(f'The converted "{param_name}" argument must be complex and, as such, '
                         f'must conform to one of the following "{supp_complex}" instead '
                         f'of "{type(test_dtlike)}"')


def _validate_read_raw_samples(filename: Path, sample_dtype: DTypeLike) -> None:
    """Validate the _read_raw_samples() arguments.

    Raises:
        FileNotFoundError: must_exist is True but validate_this is not found.
        TypeError: Bad data type.
        ValueError: Bad value.
    """
    # INPUT VALIDATION
    # filename
    validate_path(filename, 'filename', must_exist=True)
    # sample_dtype
    _validate_dtype_like(sample_dtype, 'sample_dtype', must_be_complex=False)


def _validate_sigmf_paths(basename: Path) -> Tuple[Path, Path]:
    """Use basename to form the SigMF Path objects.

    1. Validate basename
    2. Form SigMF Path objects (using basename)
    3. Validate both as files that exist

    Args:
        basename: The base filename of the SigMF dataset.

    Returns:
        A tuple containing the (data_path, meta_path).

    Raises:
        FileNotFoundError: filename is not found.
        OSError: The filename exists but filename is not a file.
        TypeError: Bad data type.
        ValueError: Bad value.
    """
    # LOCAL VARIABLES
    data_path = None  # The SigMF data filename, derived from basename
    meta_path = None  # The SigMF metadata filename, derived from basename

    # INPUT VALIDATION
    validate_path(validate_this=basename, param_name='basename', must_exist=False)  # Data type
    data_path = basename.with_suffix('.' + SIGMF_DATA_FILE_EXT)
    meta_path = basename.with_suffix('.' + SIGMF_META_FILE_EXT)
    validate_path(validate_this=data_path, param_name=f'basename.{SIGMF_DATA_FILE_EXT}',
                  must_exist=True)
    validate_path(validate_this=meta_path, param_name=f'basename.{SIGMF_META_FILE_EXT}',
                  must_exist=True)

    # DONE
    return tuple((data_path, meta_path))
