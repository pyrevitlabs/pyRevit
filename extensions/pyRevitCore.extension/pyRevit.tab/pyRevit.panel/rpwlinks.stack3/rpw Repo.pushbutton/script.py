"""Opens the git repository page for RevitPythonWrapper"""

__context__ = 'zerodoc'


url = 'https://github.com/gtalarico/revitpythonwrapper'
from pyrevit import coreutils
coreutils.open_url(url)
