"""
.NET imports

This module ensures most commonly used .NET classes are loaded for you.for

>>> from rpw.utils.dotnet import List, Enum, Process

"""

import sys

from rpw.utils.logger import logger
from rpw.utils.sphinx_compat import MockImporter

# Attempt to Import clr
try:
    import clr
except ImportError:
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
