"""Opens the website that is providing the icons for the tools."""

__context__ = 'zerodoc'


url = 'https://icons8.com/web-app/new-icons/color'
from pyrevit import coreutils
coreutils.open_url(url)
