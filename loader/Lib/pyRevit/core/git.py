""" Module name: git.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Description:
LibGit2Sharp wrapper module for pyRevit.

Documentation:
https://github.com/libgit2/libgit2sharp/wiki
"""

import importlib

import System
import clr
from .config import GIT_LIB

# todo: figure out how to import extensions on the caller's scope. Can't expect the user to import this everytime
clr.AddReference("System.Core")
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName(GIT_LIB)

# public git module
git = importlib.import_module(GIT_LIB)
