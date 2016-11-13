# doc: https://github.com/libgit2/libgit2sharp/wiki

import sys
import os.path as op
import importlib

from .config import GIT_LIB

import clr
import System

clr.AddReference("System.Core")
# todo figure out how to import extensions on the caller's scope. Can't expect the user to import this everytime.
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName(GIT_LIB)

git = importlib.import_module(GIT_LIB)
