"""Opens the pyRevit blog."""
# -*- coding=utf-8 -*-
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import script
from pyrevit.versionmgr import urls


script.open_url(urls.PYREVIT_BLOG)
