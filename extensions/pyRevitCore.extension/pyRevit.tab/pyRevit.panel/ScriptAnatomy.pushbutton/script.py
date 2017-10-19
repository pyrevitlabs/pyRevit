"""Opens the Anatomy of a Script page in the default browser."""

from pyrevit import script


__context__ = 'zerodoc'
__title__ = 'Script\nAnatomy'


url = 'http://eirannejad.github.io/pyRevit/anatomyofpyrevitscript/'
script.open_url(url)
