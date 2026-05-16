"""Opens the issue tracker on github to report bugs and issues."""
from pyrevit import script
from pyrevit.versionmgr import urls


script.open_url(urls.PYREVIT_GITHUBISSUES)
