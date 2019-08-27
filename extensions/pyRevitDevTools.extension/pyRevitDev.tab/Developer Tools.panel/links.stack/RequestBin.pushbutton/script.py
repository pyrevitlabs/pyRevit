"""Open RequestBin website that helps verifying http requests."""

from pyrevit import script


__context__ = 'zero-doc'


script.open_url('https://requestbin.fullcontact.com/')
