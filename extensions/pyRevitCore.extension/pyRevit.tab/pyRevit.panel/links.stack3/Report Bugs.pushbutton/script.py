"""Opens the issue tracker on github to report bugs and issues."""
from pyrevit import coreutils


__context__ = 'zerodoc'


url = 'https://github.com/eirannejad/pyrevit/issues'
coreutils.open_url(url)
