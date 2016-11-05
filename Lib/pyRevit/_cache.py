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

import json

# pyrevit module imports
from .config import USER_TEMP_DIR, PYREVIT_ASSEMBLY_NAME, HASH_VALUE_PARAM, HASH_VERSION_PARAM
from .exceptions import *
from .logger import logger
from ._basecomponents import *


def _get_cache_file(cached_pkg):
    return op.join(USER_TEMP_DIR,'{}_cache_{}.json'.format(PYREVIT_ASSEMBLY_NAME, cached_pkg.name))


def _serialize(obj):
    return json.dumps(obj, default=lambda o: o._get_cache_data(), sort_keys=True, indent=4)


def _cleanup_cache_files():
    pass


def _read_cache_for(cached_pkg):
    try:
        logger.debug('Reading cache for: {}'.format(cached_pkg))
        cache_file = _get_cache_file(cached_pkg)
        logger.debug('Cache file is: {}'.format(cache_file))
        with open(_get_cache_file(cached_pkg), 'r') as cache_file:
            cached_tab_dict = json.load(cache_file)
        return cached_tab_dict
    except:
        raise PyRevitCacheReadError()


def _write_cache_for(parsed_pkg):
    try:
        logger.debug('Writing cache for: {}'.format(parsed_pkg))
        cache_file = _get_cache_file(parsed_pkg)
        logger.debug('Cache file is: {}'.format(cache_file))
        with open(cache_file, 'w') as cache_file:
            cache_file.write(_serialize(parsed_pkg))
    except:
        raise PyRevitCacheWriteError()


def _update_cache(parsed_pkg):
    logger.debug('Updating cache for tab: {} ...'.format(parsed_pkg.name))
    _write_cache_for(parsed_pkg)
    logger.debug('Cache updated for tab: {}'.format(parsed_pkg.name))


def _make_components_from_cache(parent_pkg, cached_tab_dict):
    # fixme: complete load function
    # parent_pkg._load_cache_data({})
    pass


def _get_cached_package(cached_pkg):
    cached_tab_dict = _read_cache_for(cached_pkg)
    try:
        logger.debug('Constructing components from cache for: {}'.format(cached_pkg))
        _make_components_from_cache(cached_pkg, cached_tab_dict)
        logger.debug('Load successful...')
    except:
        logger.debug('Error reading cache...')
        raise PyRevitCacheError()


def _is_cache_valid(pkg):
    try:
        cached_tab_dict = _read_cache_for(pkg)
        logger.debug('Package cache version is: {} for: {}'.format(pkg.hash_version, pkg))
        cache_version_valid = cached_tab_dict[HASH_VERSION_PARAM] == pkg.hash_version

        logger.debug('Package hash value is: {} for: {}'.format(pkg.hash_value, pkg))
        cache_hash_valid = cached_tab_dict[HASH_VALUE_PARAM] == pkg.hash_value

        # cache is valid if both version and hash value match
        return cache_version_valid and cache_hash_valid

    except Exception as err:
        logger.debug('Can not read cache file for: {} | {}'.format(pkg, err))
