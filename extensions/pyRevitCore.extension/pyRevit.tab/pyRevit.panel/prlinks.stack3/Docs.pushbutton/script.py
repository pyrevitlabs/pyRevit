"""Opens the documentation page."""

__context__ = 'zerodoc'


url = 'http://pyrevit.readthedocs.io/en/latest/'
from pyrevit import coreutils
coreutils.open_url(url)
