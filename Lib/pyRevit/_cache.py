import os
import sys
import os.path as op
import shutil
import re
import json
import hashlib
from datetime import datetime

# pyrevit module imports
from .config import USER_TEMP_DIR, PYREVIT_ASSEMBLY_NAME, PyRevitVersion
from .exceptions import *
from .logger import logger
from .uielements import *

# dot net imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')
from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Diagnostics import Process

# revit api imports
from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *


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
