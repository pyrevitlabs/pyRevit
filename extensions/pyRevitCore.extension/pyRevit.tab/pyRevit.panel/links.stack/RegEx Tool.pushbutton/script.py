"""Opens RegExr website that is used to create and test regular expressions."""
from pyrevit import script


__context__ = 'zero-doc'


url = 'http://regexr.com/'
script.open_url(url)
