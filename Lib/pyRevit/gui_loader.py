""" pyRevit Loder Test
pyRevit is an open source project managed by Ehsan Iran-Nejad
https://github.com/eirannejad

Goals of this exercise:
- Encapsulate Concerns into separate Modules (Parsing, Assembly, UI Elements)
- Create Class wrappers for revit Objects, match Revit names when possible
  Wrappers all have a attribute revit_XXX that stores reference to
  the actual revit object
- Explicit variable names, recommended variable_naming_style,
  keyword args for complex functions/objects.
- Explicit model loader
- Use Process PID to idendify re-loading "session".
- Improve code maintainability, extensibility.
- Learn how loader works.
- Testing Caching by pickling the entire session

"""

import clr
import sys
import os
from os import path
import re
import logging

#  Set CWD
cwd = os.path.dirname(__file__)
sys.path.append(cwd)
os.chdir(cwd)

from loader.logger import logger
from loader.config import TEMPDIR, SCRIPTS_DIR, CACHE_FILE
from loader.assemblies import make_scripts_dll, get_cmd_loader_base
from loader.parsers import parse_directory, parse_files, print_parsed_ribbon
from loader.uielements import Ribbon
from loader.utils import load_session, dump_session
from loader.utils import purge_unused_dlls, Timer, get_hash_from_dir
timer = Timer()

VERBOSE = False
logger.verbose(VERBOSE)

cached_session_hash, cached_session_data = load_session()

session_hash = get_hash_from_dir(SCRIPTS_DIR)
if cached_session_hash == session_hash:
    logger.info('Directory has NOT changed. Reloading Cached Session...')
    ribbon = cached_session_data
else:
    logger.info('Directory HAS changed. Parsing directory...')
    ribbon = parse_directory(SCRIPTS_DIR)

cmd_loader_base = get_cmd_loader_base()
dll_path, dll_filename = make_scripts_dll(cmd_loader_base, ribbon.commands)

is_reloading = path.exists(path.join(TEMPDIR, CACHE_FILE))
if is_reloading:
    logger.title('Reloading Session')
else:
    logger.title('New Session')
    purge_unused_dlls(dll_filename)

dump_session(ribbon)
ribbon.create(dll_path, is_reloading=is_reloading)

if VERBOSE:
    print_parsed_ribbon(ribbon)

loading_time = timer.stop()
logger.info('Done [{} sec]'.format(loading_time))

if not logger.errors:
    pass
    __window__.Close()
else:
    pass
    # print(logger.errors)
