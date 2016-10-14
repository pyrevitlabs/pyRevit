import sys
import os
import os.path as op
import re
import importlib

import pyRevit.utils as utils
import pyRevit.config as cfg
from pyRevit.exceptions import GitError
from pyRevit.logger import logger

sys.path.append(op.join(cfg.LOADER_DIR, cfg.GIT_LIB))

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference("System.Core")

import System
clr.ImportExtensions(System.Linq)

clr.AddReferenceByName(cfg.GIT_LIB)
git = importlib.import_module(cfg.GIT_LIB)

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
