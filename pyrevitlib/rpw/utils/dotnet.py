"""
.NET imports

This module ensures most commonly used .NET classes are loaded for you.for

>>> from rpw.utils.dotnet import List, Enum, Process

"""

import sys

from rpw.utils.logger import logger

# Attempt to Import clr
try:
    import clr
except ImportError:
    from rpw.utils.sphinx_compat import MockImporter
    # Running Sphinx. Import MockImporter
    logger.warning('Error Importing CLR. Loading Mock Importer')
    sys.meta_path.append(MockImporter())

################
# .NET IMPORTS #
################

import clr
clr.AddReference('System')                 # Enum, Diagnostics
clr.AddReference('System.Collections')     # List

# Core Imports
from System import Enum
from System.Collections.Generic import List
from System.Diagnostics import Process


def to_clr_list(item_type, values):
    """Build a generic CLR list without relying on Python collection coercion.

    Args:
        item_type (type): CLR type accepted by the target API.
        values (iterable): Values to add to the returned list.

    Returns:
        System.Collections.Generic.List[item_type]: Values in input order.
    """
    result = List[item_type]()
    for value in values:
        result.Add(value)
    return result
