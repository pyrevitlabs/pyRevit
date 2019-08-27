"""Opens the git repository page for RevitPythonWrapper."""
from pyrevit import script


__context__ = 'zero-doc'


url = 'https://github.com/gtalarico/revitpythonwrapper'
script.open_url(url)
