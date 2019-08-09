"""Opens RegExr website that is used to create and test regular expressions."""
from pyrevit import script


__context__ = 'zerodoc'


url = 'http://regexr.com/'
script.open_url(url)
