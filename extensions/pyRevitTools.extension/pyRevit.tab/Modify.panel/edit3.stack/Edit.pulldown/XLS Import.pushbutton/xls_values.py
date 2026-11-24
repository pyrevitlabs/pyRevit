# -*- coding: utf-8 -*-
"""Cell value parsing for XLS Import.

Pure Python without Revit API access, so it imports on every engine and runs
in the API-free test suite. Every function raises ``ValueError`` with a
user-readable message for a value that must not be written to a parameter.
"""

import math
import numbers
import re

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1
WHOLE_NUMBER_TEXT_LIMIT = 1e15

try:
    basestring  # noqa: B018 pylint: disable=used-before-assignment
except NameError:
    basestring = str

TEXT_TYPES = (basestring,)
WHITESPACE_PATTERN = re.compile(r"\s+", re.UNICODE)

YES_LABELS = frozenset("yes true 1 y ja oui sí si sim да 예 是".split())
NO_LABELS = frozenset("no false 0 n nein non não nao нет 아니요 否".split())


def parse_number(value):
    """Convert a numeric or text cell to a finite float.

    Text cells accept a decimal point or a decimal comma. When both
    separators appear, the last one is the decimal separator and the other
    groups thousands. A lone comma followed by exactly three digits
    (``1,234``) is ambiguous and rejected.

    Args:
        value: A float from a numeric cell, or the text of a cell.

    Returns:
        float: The parsed number.

    Raises:
        ValueError: If the value is not a finite number or is ambiguous.
    """
    if isinstance(value, TEXT_TYPES):
        number = _parse_number_text(value)
    else:
        number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("'{}' is not a finite number".format(value))
    return number


def parse_whole_number(value):
    """Convert a cell to an integer that fits a Revit Integer parameter.

    Args:
        value: A float from a numeric cell, or the text of a cell.

    Returns:
        int: The value as a signed 32-bit integer.

    Raises:
        ValueError: If the value is not a whole number or is outside the
            signed 32-bit range.
    """
    number = parse_number(value)
    if number != math.floor(number):
        raise ValueError("'{}' is not a whole number".format(value))
    whole_number = int(number)
    if not INT32_MIN <= whole_number <= INT32_MAX:
        raise ValueError("'{}' is outside the range of an Integer".format(value))
    return whole_number


def parse_yes_no(value):
    """Convert a cell to 1 (Yes) or 0 (No) for a Yes/No parameter.

    Accepts the numbers 1 and 0, the words yes/no and true/false, and the
    Yes/No labels of the languages pyRevit is translated to.

    Args:
        value: A float from a numeric cell, or the text of a cell.

    Returns:
        int: 1 or 0.

    Raises:
        ValueError: If the value is neither a Yes nor a No.
    """
    if isinstance(value, TEXT_TYPES):
        label = value.strip().lower()
        if label in YES_LABELS:
            return 1
        if label in NO_LABELS:
            return 0
    try:
        number = parse_number(value)
    except ValueError:
        number = None
    if number in (0, 1):
        return int(number)
    raise ValueError("'{}' is not a Yes/No value".format(value))


def format_text_value(value):
    """Convert a cell to the text stored in a String parameter.

    Excel returns every number as a float, so a number typed into a text
    column is written without a trailing ``.0`` when it is whole, and with
    the 15 significant digits Excel displays otherwise (``repr`` would give
    ``5.7000000000000002`` on IronPython 3).

    Args:
        value: A float from a numeric cell, or the text of a cell.

    Returns:
        str: The text to store.
    """
    if isinstance(value, TEXT_TYPES):
        return value
    if isinstance(value, numbers.Real):
        number = float(value)
        if number == math.floor(number) and abs(number) < WHOLE_NUMBER_TEXT_LIMIT:
            return str(int(number))
        return "%.15g" % number
    return str(value)


def _parse_number_text(text):
    text = text.strip().replace(" ", "").replace(" ", "")
    has_dot = "." in text
    has_comma = "," in text
    if has_dot and has_comma:
        decimal_separator = "." if text.rfind(".") > text.rfind(",") else ","
        group_separator = "," if decimal_separator == "." else "."
        text = text.replace(group_separator, "").replace(decimal_separator, ".")
    elif has_comma:
        digits_after_last_comma = len(text) - text.rfind(",") - 1
        if text.count(",") == 1 and digits_after_last_comma == 3:
            raise ValueError(
                "'{}' is ambiguous: write it with a decimal point".format(text)
            )
        if text.count(",") == 1:
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    return float(text)
