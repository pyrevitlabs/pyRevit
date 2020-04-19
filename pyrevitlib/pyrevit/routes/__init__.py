"""HTTP API framework similar to flask."""
# types to be exported
#pylint: disable=wildcard-import,redefined-outer-name,unused-variable
from pyrevit.routes.server import *

def active_routes_api():
    """Activates routes API"""
    from pyrevit.routes.api import *
