"""Opens the Anatomy of a Script page in the default browser."""

from pyrevit import script
from pyrevit.versionmgr import urls


__context__ = 'zero-doc'
__title__ = 'Script\nAnatomy'


script.open_url(urls.PYREVIT_BLOG_SCRIPTANAT)
