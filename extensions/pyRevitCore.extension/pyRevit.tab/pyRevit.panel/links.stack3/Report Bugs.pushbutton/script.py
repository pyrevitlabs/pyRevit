"""Opens the issue tracker on github to report bugs and issues."""

__context__ = 'zerodoc'


url = 'https://github.com/eirannejad/pyrevit/issues'
from pyrevit import coreutils
coreutils.open_url(url)
