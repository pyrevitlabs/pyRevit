"""Opens the wiki page."""
from pyrevit import script
from pyrevit.versionmgr import urls


__context__ = 'zero-doc'


script.open_url(urls.PYREVIT_WIKI)
