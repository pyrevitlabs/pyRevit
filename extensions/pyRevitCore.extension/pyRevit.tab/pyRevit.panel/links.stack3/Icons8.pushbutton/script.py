"""Opens the website that is providing the icons for the tools."""
from pyrevit import script


__context__ = 'zerodoc'


url = 'https://icons8.com/icon/set/revit/windows'
script.open_url(url)
