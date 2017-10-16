"""Opens the Anatomy of a Script page in the default browser."""

__context__ = 'zerodoc'

__title__ = 'Script\nAnatomy'


url = 'http://eirannejad.github.io/pyRevit/anatomyofpyrevitscript/'
from pyrevit import coreutils
coreutils.open_url(url)
