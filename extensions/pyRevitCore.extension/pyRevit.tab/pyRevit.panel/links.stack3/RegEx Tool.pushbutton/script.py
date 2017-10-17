"""Opens RegExr website that is used to create and test regular expressions."""
from pyrevit import coreutils


__context__ = 'zerodoc'


url = 'http://regexr.com/'
coreutils.open_url(url)
