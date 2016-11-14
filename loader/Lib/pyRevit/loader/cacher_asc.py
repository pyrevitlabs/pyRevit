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

import os.path as op
import json

from ..logger import get_logger
logger = get_logger(__name__)

# pyrevit module imports
from ..config import USER_TEMP_DIR, SESSION_ID, HASH_VALUE_PARAM, HASH_VERSION_PARAM, SUB_CMP_KEY
from ..exceptions import PyRevitCacheError, PyRevitCacheReadError, PyRevitCacheWriteError
from ..utils import get_all_subclasses


def _get_cache_file(cached_pkg):
    return op.join(USER_TEMP_DIR, '{}_cache_{}.json'.format(SESSION_ID, cached_pkg.name))


def _make_cache_from_cmp(obj):
    return json.dumps(obj, default=lambda o: o.get_cache_data(), sort_keys=True, indent=4)


def _make_sub_cmp_from_cache(parent_cmp, cached_sub_cmps):
    logger.debug('Processing cache for: {}'.format(parent_cmp))
    # get allowed classes under this component
    allowed_sub_cmps = get_all_subclasses(parent_cmp.allowed_sub_cmps)
    logger.debug('Allowed sub components are: {}'.format(allowed_sub_cmps))
    # iterate through list of cached sub components
    for cached_cmp in cached_sub_cmps:  # type: dict
        for sub_class in allowed_sub_cmps:
            if sub_class.type_id == cached_cmp['type_id']:
                logger.debug('Creating sub component from cache: {}, {}'.format(cached_cmp['name'], sub_class))

                # cached_cmp might contain SUB_CMP_KEY. This needs to be removed since this function will make
                # all the children recursively. So if this component has SUB_CMP_KEY means it has sub components:
                sub_cmp_cache = None
                if SUB_CMP_KEY in cached_cmp.keys():
                    # drop subcomponents dict from cached_cmp since we don't want the loaded_cmp to include this
                    sub_cmp_cache = cached_cmp.pop(SUB_CMP_KEY)

                # create sub component from cleaned cached_cmp
                loaded_cmp = sub_class()
                loaded_cmp.load_cache_data(cached_cmp)

                # now process sub components for loaded_cmp if any
                if sub_cmp_cache:
                    _make_sub_cmp_from_cache(loaded_cmp, sub_cmp_cache)

                parent_cmp.add_component(loaded_cmp)


def _cleanup_cache_files():
    # todo: cleanup cache files?
    pass


def _read_cache_for(cached_pkg):
    try:
        logger.debug('Reading cache for: {}'.format(cached_pkg))
        cache_file = _get_cache_file(cached_pkg)
        logger.debug('Cache file is: {}'.format(cache_file))
        with open(_get_cache_file(cached_pkg), 'r') as cache_file:
            cached_tab_dict = json.load(cache_file)
        return cached_tab_dict
    except Exception as err:
        raise PyRevitCacheReadError('Error reading cache for: {} | {}'.format(cached_pkg, err))


def _write_cache_for(parsed_pkg):
    try:
        logger.debug('Writing cache for: {}'.format(parsed_pkg))
        cache_file = _get_cache_file(parsed_pkg)
        logger.debug('Cache file is: {}'.format(cache_file))
        with open(cache_file, 'w') as cache_file:
            cache_file.write(_make_cache_from_cmp(parsed_pkg))
    except Exception as err:
        raise PyRevitCacheWriteError('Error writing cache for: {} | {}'.format(parsed_pkg, err))


def update_cache(parsed_pkg):
    logger.debug('Updating cache for tab: {} ...'.format(parsed_pkg.name))
    _write_cache_for(parsed_pkg)
    logger.debug('Cache updated for tab: {}'.format(parsed_pkg.name))


def get_cached_package(installed_pkg):
    cached_pkg_dict = _read_cache_for(installed_pkg)
    try:
        logger.debug('Constructing components from cache for: {}'.format(installed_pkg))
        # get cached sub component dictionary and call recursive maker function
        _make_sub_cmp_from_cache(installed_pkg, cached_pkg_dict.pop(SUB_CMP_KEY))
        logger.debug('Load successful...')
    except Exception as err:
        logger.debug('Error reading cache...')
        raise PyRevitCacheError(err)

    return installed_pkg


def is_cache_valid(pkg):
    # fixme: clean cache file if it is not valid
    try:
        cached_pkg_dict = _read_cache_for(pkg)  # type: dict
        logger.debug('Package cache version is: {} for: {}'.format(pkg.hash_version, pkg))
        cache_version_valid = cached_pkg_dict[HASH_VERSION_PARAM] == pkg.hash_version

        logger.debug('Package hash value is: {} for: {}'.format(pkg.hash_value, pkg))
        cache_hash_valid = cached_pkg_dict[HASH_VALUE_PARAM] == pkg.hash_value

        # cache is valid if both version and hash value match
        return cache_version_valid and cache_hash_valid

    except PyRevitCacheReadError as err:
        logger.debug(err)
        return False

    except Exception as err:
        logger.debug('Error determining cache validity: {} | {}'.format(pkg, err))
