"""Helper functions for python."""


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
