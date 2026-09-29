# pyrevit.compat hands back the engine-appropriate requests: the vendored one under
# CPython, and the HttpClient-backed shim under IronPython, where the vendored
# urllib3 cannot build a TLS context. #3638.
from pyrevit.compat import requests


r = requests.get("http://www.x.com")

print("X.com says: {}".format(r.text))
