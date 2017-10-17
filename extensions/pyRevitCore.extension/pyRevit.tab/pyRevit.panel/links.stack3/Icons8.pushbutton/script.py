"""Opens the website that is providing the icons for the tools."""
from pyrevit import coreutils


__context__ = 'zerodoc'


url = 'https://icons8.com/web-app/new-icons/color'
coreutils.open_url(url)
