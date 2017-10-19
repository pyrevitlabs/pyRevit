"""Opens the documentation page."""
from pyrevit import script


__context__ = 'zerodoc'


url = 'http://pyrevit.readthedocs.io/en/latest/'
script.open_url(url)
