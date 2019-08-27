"""Opens the documentation page for RevitPythonWrapper."""
from pyrevit import script


__context__ = 'zero-doc'


url = 'http://revitpythonwrapper.readthedocs.io/en/latest/'
script.open_url(url)
