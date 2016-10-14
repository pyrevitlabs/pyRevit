import sys
import os
import os.path as op
import re
import importlib

from .config import LOADER_DIR, GIT_LIB
from .logger import logger

sys.path.append(op.join(LOADER_DIR, GIT_LIB))

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference("System.Core")

import System
# todo figure out how to import extensions on the caller's scope. Can't expect the user to import this everytime.
clr.ImportExtensions(System.Linq)

clr.AddReferenceByName(GIT_LIB)
git = importlib.import_module(GIT_LIB)

# todo rewrite update mechanism to use this to update all(?) extensions

# from pyRevit.git import git
# repo = git.Repository(r'C:\Users\eirannejad\AppData\Roaming\pyRevit\pyRevitDev')
# for c in repo.Diff.Compare[git.TreeChanges]():
#     print(c)
#
#
# from pyRevit.git import git
# repo = git.Repository(r'C:\Users\eirannejad\AppData\Roaming\pyRevit\pyRevitDev')
# for c in repo.Diff.Compare(repo.Head.Tip.Parents.Single().Tree, repo.Head.Tip.Tree):
#     print(c)
