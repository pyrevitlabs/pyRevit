"""Opens the git repository page."""

__context__ = 'zerodoc'


url = 'https://github.com/eirannejad/pyRevit'
from pyrevit import coreutils
coreutils.open_url(url)
