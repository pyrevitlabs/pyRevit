"""Opens the git repository page."""
from pyrevit import script


__context__ = 'zerodoc'


url = 'https://github.com/eirannejad/pyRevit'
script.open_url(url)
