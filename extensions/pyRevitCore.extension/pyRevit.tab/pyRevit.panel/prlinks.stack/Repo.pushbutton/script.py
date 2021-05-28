"""Opens the git repository page."""
from pyrevit import script
from pyrevit.versionmgr import urls


script.open_url(urls.PYREVIT_GITHUB)
