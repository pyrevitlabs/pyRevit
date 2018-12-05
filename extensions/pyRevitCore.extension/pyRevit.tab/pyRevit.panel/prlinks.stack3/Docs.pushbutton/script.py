"""Opens the documentation page."""
from pyrevit import script
from pyrevit.versionmgr import urls


__context__ = 'zerodoc'


script.open_url(urls.docs)
