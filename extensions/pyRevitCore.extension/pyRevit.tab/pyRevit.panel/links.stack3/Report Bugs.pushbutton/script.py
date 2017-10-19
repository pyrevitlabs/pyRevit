"""Opens the issue tracker on github to report bugs and issues."""
from pyrevit import script


__context__ = 'zerodoc'


url = 'https://github.com/eirannejad/pyrevit/issues'
script.open_url(url)
