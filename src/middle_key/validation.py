"""Functionality to validate input."""

# Standard Imports
from pathlib import Path
from typing import Any, Final
# Third Party Imports
# Local Imports


# Template string for arguments of the wrong data type
BAD_TYPE: Final[str] = 'The "{}" argument should have been of type "{}" but was "{}" instead'
# Template string for arguments that may not be empty
BAD_VAL_EMPTY: Final[str] = 'The "{}" argument can not be empty'


def validate_bool(validate_this: bytes, param_name: str) -> None:
    """Validate a variable as a bool.

    Args:
        validate_this: An object to validate as a bool.
        param_name: The name of the parameter to be used in exception messages.

    Raises:
        TypeError: Invalid data type.
    """
    validate_type(var=validate_this, var_name=param_name, var_type=bool)


def validate_int(validate_this: int, param_name: str) -> None:
    """Validate validate_this as an int object.

    Args:
        validate_this: The parameter to validate.
        param_name: The name of the parameter to be used in exception messages.

    Raises:
        TypeError: validate_this is not an int.
    """
    # VALIDATION
    validate_type(validate_this, param_name, int)


def validate_path(validate_this: Path, param_name: str, must_exist: bool = True) -> None:
    """Validate validate_this as a Path object to a path that exists.

    Args:
        validate_this: A Path object to a path that exists.
        param_name: The name of the parameter to be used in exception messages.
        must_exist: Optional; If False, ignores missing files.

    Raises:
        FileNotFoundError: must_exist is True but validate_this is not found.
        TypeError: validate_this is not a Path object.
    """
    # INPUT VALIDATION
    validate_string(param_name, 'param_name', can_be_empty=True)
    validate_bool(must_exist, 'must_exist')
    validate_type(validate_this, param_name, Path)
    if must_exist and not validate_this.exists():
        raise FileNotFoundError(f'Unable to locate "{param_name}" path: '
                                f'"{str(validate_this.absolute())}"')


def validate_string(validate_this: str, param_name: str, can_be_empty: bool = False) -> None:
    """Standardizes how this module validates string parameters.

    Verifies validate_this is a string. Type validation is handled by validate_type().

    Args:
        validate_this: The parameter to validate.
        param_name: The name of the parameter to be used in exception messages.
        can_be_empty: Optional; If False, this function verifies validate_this is not empty.

    Raises:
        TypeError: validate_this is not a string.
        ValueError: validate_this is empty and can_be_empty is False.
    """
    # VALIDATION
    validate_type(validate_this, param_name, str)
    if not validate_this and not can_be_empty:
        raise ValueError(BAD_VAL_EMPTY.format(param_name))


def validate_type(var: Any, var_name: str, var_type: type) -> None:
    """Standardizes how variables are type-validated.

    Verifies var is the same type represented in var_type. This function does not validate input.

    Args:
        var: The variable to type-validate.
        var_name: The name of the variable to be used in exception messages.
        var_type: The expected variable type.

    Raises:
        TypeError: Invalid data type.
    """
    if not _validate_type(var, var_type):
        raise TypeError(BAD_TYPE.format(var_name, var_type, type(var)))


def _validate_type(var: Any, var_type: type) -> bool:
    """Standardizes how variables are evaluated against a data type.

    Args:
        var: The variable to type-validate.
        var_type: The expected variable type.

    Returns:
        True if var is of type var_type, False otherwise.
    """
    # LOCAL VARIABLES
    is_valid = False  # Is var of type var_type?

    # VALIDATE IT
    if isinstance(var, var_type):
        is_valid = True

    # DONE
    return is_valid
