"""
Description:
LibGit2Sharp wrapper module for pyRevit.

Documentation:
https://github.com/libgit2/libgit2sharp/wiki
"""

import clr
import importlib

# noinspection PyUnresolvedReferences
import System

GIT_LIB = 'LibGit2Sharp'

# todo: figure out how to import extensions on the caller's scope. Can't expect the user to import this everytime
clr.AddReference("System.Core")
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName(GIT_LIB)

# public git module
git = importlib.import_module(GIT_LIB)
