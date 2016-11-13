# doc: https://github.com/libgit2/libgit2sharp/wiki

import sys
import os.path as op
import importlib

from .config import LOADER_ASM_DIR, GIT_LIB_DIR

import clr
import System

sys.path.append(op.join(LOADER_ASM_DIR, GIT_LIB_DIR))
clr.AddReference("System.Core")
# todo figure out how to import extensions on the caller's scope. Can't expect the user to import this everytime.
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName(GIT_LIB_DIR)

git = importlib.import_module(GIT_LIB_DIR)
