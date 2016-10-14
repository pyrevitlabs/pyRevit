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
clr.AddReferenceByName(cfg.GIT_LIB)
git = importlib.import_module('LibGit2Sharp')
