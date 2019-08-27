"""Opens the documentation page."""
from pyrevit import script
from pyrevit.versionmgr import urls


__context__ = 'zero-doc'


script.open_url(urls.PYREVIT_DOCS)
