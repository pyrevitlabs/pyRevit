""" Module name = _cache.py
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
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This module is reponsible for caching the information provided by _parse, _assemblies, or _ui. All these modules can
ask cache to store/recover information to speed up the session load process.

All these four modules are private and handled by pyRevit.session
These modules do not import each other and mainly use base modules (.config, .logger, .exceptions, .output, .utils)
All these four modules can understand the component tree. (_basecomponents module)
 _parser parses the folders and creates a tree of components provided by _basecomponents
 _assemblies make a dll from the tree.
 _ui creates the ui using the information provided by the tree.
 _cache will save and restore the tree to increase loading performance.
"""

import shutil
import re
import json
import hashlib

# pyrevit module imports
from .config import USER_TEMP_DIR, PYREVIT_ASSEMBLY_NAME, PyRevitVersion
from .exceptions import *
from .logger import logger
from .uielements import *

# todo cache can store cached dll info as well
# todo cache needs to save home directory address in cache and cross check later


def calculate_hash(self):
    """Creates a unique hash # to represent state of directory."""
    # logger.info('Generating Hash of directory')
    # search does not include png files:
    #   if png files are added the parent folder mtime gets affected
    #   cache only saves the png address and not the contents so they'll get loaded everytime
    # todo: improve speed by pruning dir: dirs[:] = [d for d in dirs if d not in excludes]
    #       see http://stackoverflow.com/a/5141710/2350244
    pat = r'(\.panel)|(\.tab)'
    patfile = r'(\.py)'
    mtime_sum = 0
    for root, dirs, files in os.walk(self.tabFolder):
        if re.search(pat, root, flags=re.IGNORECASE):
            mtime_sum += op.getmtime(root)
            for filename in files:
                if re.search(patfile, filename, flags=re.IGNORECASE):
                    modtime = op.getmtime(op.join(root, filename))
                    mtime_sum += modtime
    return hashlib.md5(str(mtime_sum)).hexdigest()


def get_cache_file(cached_tab):
    return op.join(USER_TEMP_DIR,'{}_cache_{}.json'.format(PYREVIT_ASSEMBLY_NAME, cached_tab.tabName))


def serialize(obj):
    cache_dict_str = json.dumps(obj, default=lambda o: o.get_clean_dict(), sort_keys=True, indent=4)
    return '{\n' + '    "cacheVersion": "{}", '.format(PyRevitVersion.full_version_as_str()) + cache_dict_str[1:]


def cleanup_cache_files():
    pass


def read_cache_for(cached_tab):
    try:
        with open(get_cache_file(cached_tab), 'r') as cache_file:
            cached_tab_dict = json.load(cache_file)
        return cached_tab_dict
    except:
        raise PyRevitCacheReadError()


def write_cache_for(parsed_tab):
    try:
        with open(get_cache_file(parsed_tab), 'w') as cache_file:
            cache_file.write(serialize(parsed_tab))
    except:
        raise PyRevitCacheWriteError()


def update_cache(parsed_tab):
    logger.debug('Updating cache for tab: {} ...'.format(parsed_tab.name))
    if not parsed_tab.loaded_from_cache:
        logger.debug('Writing cache for tab: {}'.format(parsed_tab.name))
        write_cache_for(parsed_tab)
        logger.debug('Cache updated for tab: {}'.format(parsed_tab.name))
    else:
        logger.debug('Cache is up-to-date for tab: {}'.format(parsed_tab.tabName))


def get_cached_tab(cached_tab):
    logger.debug('Checking if tab directory has any changes, otherwise loading from cache...')
    logger.debug('Current hash is: {}'.format(cached_tab.tabHash))
    cached_tab_dict = read_cache_for(cached_tab)
    try:
        if cached_tab_dict['tabHash'] == cached_tab.tabHash         \
        and cached_tab_dict['cacheVersion'] == PyRevitVersion.full_version_as_str():
            logger.debug('Cache is up-to-date for tab: {}'.format(cached_tab.tabName))
            logger.debug('Loading from cache...')
            cached_tab.load_from_cache(cached_tab_dict)
            logger.debug('Load successful...')
        else:
            logger.debug('Cache is expired...')
            raise PyRevitCacheExpiredError()
    except:
        logger.debug('Error reading cache...')
        raise PyRevitCacheError()


def get_cached_package(cached_pkg):
    for cached_tab in cached_pkg:
        get_cached_package(cached_tab)


def is_cached_tab_valid(cached_tab):
    pass


def is_cache_valid(cached_pkg):
    for cached_tab in cached_pkg:
        if not is_cached_tab_valid(cached_tab):
            return False
    return True
