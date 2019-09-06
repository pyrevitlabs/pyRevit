"""Opens the pyRevit blog."""
# -*- coding=utf-8 -*-
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import script
from pyrevit.versionmgr import urls


__context__ = 'zero-doc'
__title__ = {
    'en_us': "Blog",
    'fa': "وبلاگ",
    'ar': "بلاگ",
}

script.open_url(urls.PYREVIT_BLOG)
