"""Opens the developer docs page."""
from pyrevit import script
from pyrevit.versionmgr import urls


__context__ = 'zero-doc'
__title__ = "Developer\nDocs"


script.open_url(urls.PYREVIT_DOCS)
