"""Exercises the full-frame engine by making a real HTTP request.

Imports requests through pyrevit.compat, which hands back the vendored copy
under CPython and the HttpClient-backed shim under IronPython. The vendored copy
reaches TLS through urllib3, which IronPython cannot drive, so importing it
directly made this test fail on the default engine. #3638.
"""

from pyrevit.compat import requests


response = requests.get("http://www.x.com")

print("X.com responded with HTTP {}".format(response.status_code))
print("X.com says: {}".format(response.text))
