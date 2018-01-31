"""Helper functions for python."""

import re


def pairwise(iterable):
    """Iterate through items in pairs.

    Args:
        iterable (iterable): any iterable object

    Returns:
        iterable: list of pairs

    Example:
        >>> pairwise([1, 2, 3, 4, 5])
        [(1, 2), (3, 4)]    # 5 can not be paired
    """
    # a, b = tee(iterable)
    # next(b, None)
    # return izip(a, b)
    a = iter(iterable)
    return zip(a, a)


def safe_cast(val, to_type, default=None):
    """Convert value to type gracefully.

    This method basically calls to_type(value) and returns the default
    if exception occurs.

    Args:
        val (any): value to be converted
        to_type (type): target type
        default (any): value to rerun on conversion exception

    Example:
        >>> safe_cast('name', int, default=0)
        0
    """
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default


def isnumber(token):
    """Verify if given string token is int or float.

    Args:
        token (str): string value

    Returns:
        bool: True of token is int or float

    Example:
        >>> isnumber('12.3')
        True
    """
    return re.match("^[0-9.]+?$", token) is not None
