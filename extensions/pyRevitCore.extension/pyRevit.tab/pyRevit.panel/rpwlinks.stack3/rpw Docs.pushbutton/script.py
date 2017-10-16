"""Opens the documentation page for RevitPythonWrapper."""

__context__ = 'zerodoc'


url = 'http://revitpythonwrapper.readthedocs.io/en/latest/'
from pyrevit import coreutils
coreutils.open_url(url)
