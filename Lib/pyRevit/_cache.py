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


class PyRevitCache:
    def __init__(self):
        pass

    def get_cache_file(self, script_tab):
        return op.join(USER_TEMP_DIR,'{}_cache_{}.json'.format(PYREVIT_ASSEMBLY_NAME, script_tab.tabName))

    def cleanup_cache_files(self):
        pass

    def load_tab(self, script_tab):
        logger.debug('Checking if tab directory has any changes, otherwise loading from cache...')
        logger.debug('Current hash is: {}'.format(script_tab.tabHash))
        cached_tab_dict = self.read_cache_for(script_tab)
        try:
            if cached_tab_dict['tabHash'] == script_tab.tabHash         \
            and cached_tab_dict['cacheVersion'] == PyRevitCache.get_version():
                logger.debug('Cache is up-to-date for tab: {}'.format(script_tab.tabName))
                logger.debug('Loading from cache...')
                script_tab.load_from_cache(cached_tab_dict)
                logger.debug('Load successful...')
            else:
                logger.debug('Cache is expired...')
                raise PyRevitCacheExpiredError()
        except:
            logger.debug('Error reading cache...')
            raise PyRevitCacheError()

    def update_cache(self, script_tabs):
        logger.debug('Updating cache for {} tabs...'.format(len(script_tabs)))
        for script_tab in script_tabs:
            if not script_tab.loaded_from_cache:
                logger.debug('Writing cache for tab: {}'.format(script_tab.tabName))
                self.write_cache_for(script_tab)
                logger.debug('Cache updated for tab: {}'.format(script_tab.tabName))
            else:
                logger.debug('Cache is up-to-date for tab: {}'.format(script_tab.tabName))

    def read_cache_for(self, script_tab):
        try:
            with open(self.get_cache_file(script_tab), 'r') as cache_file:
                cached_tab_dict = json.load(cache_file)
            return cached_tab_dict
        except:
            raise PyRevitCacheReadError()

    def write_cache_for(self, script_tab):
        with open(self.get_cache_file(script_tab), 'w') as cache_file:
            cache_file.write(self.serialize(script_tab))

    def serialize(self, obj):
        cache_dict_str = json.dumps(obj, default=lambda o: o.get_clean_dict(), sort_keys=True, indent=4)
        return  '{\n' + '    "cacheVersion": "{}", '.format(PyRevitCache.get_version()) + cache_dict_str[1:]

    @staticmethod
    def get_version():
        return PyRevitVersion.full_version_as_str()
