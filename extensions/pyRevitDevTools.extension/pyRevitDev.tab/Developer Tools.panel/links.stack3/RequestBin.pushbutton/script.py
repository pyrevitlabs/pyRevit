"""Open RequestBin website that helps verifying http requests."""

from pyrevit import script


__context__ = 'zerodoc'


script.open_url('http://requestb.in/')
