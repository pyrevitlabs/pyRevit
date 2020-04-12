#pylint: disable=dangerous-default-value,invalid-name
#pylint: disable=import-error,invalid-name,broad-except,dangerous-default-value,missing-docstring
from pyrevit import HOST_APP
from pyrevit.labs import TargetApps
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader import sessioninfo

from pyrevit.routes import router
from pyrevit.routes import serverinfo


mlogger = get_logger(__name__)


REVITCTRL = TargetApps.Revit.RevitController


class API(object):
    """API root object

    Args:
        name (str): URL-safe unique root name of the API

    Example:
        >>> from pyrevit import routes
        >>> api = routes.API("pyrevit-core")
        >>> @api.route('/sessions/', methods=['POST'])
        >>> def reload_pyrevit(uiapp):
        ...     new_session_id = sessionmgr.reload_pyrevit()
        ...     return {"session_id": new_session_id}
    """
    def __init__(self, name):
        self.name = name

    def route(self, pattern, methods=['GET']):
        """Define a new route on this API."""
        def __func_wrapper__(f):
            for method in methods:
                router.add_route(
                    api_name=self.name,
                    pattern=pattern,
                    method=method,
                    handler_func=f
                    )
            return f
        return __func_wrapper__


# =============================================================================
# routes server base API
PYREVIT_ROUTES_API = API('routes')
# =============================================================================


# GET /status
@PYREVIT_ROUTES_API.route('/status', methods=['GET'])
def get_status():
    """Get server status"""
    return {
        "host": HOST_APP.pretty_name,
        "username": HOST_APP.username,
        "session_id": sessioninfo.get_session_uuid(),
        }

# GET /sisters
@PYREVIT_ROUTES_API.route('/sisters', methods=['GET'])
def get_sisters():
    """Get other servers running on the same machine"""
    # return [x.get_cache_data() for x in serverinfo.get_registered_servers()]
    return []


# GET /sisters/<int:year>
@PYREVIT_ROUTES_API.route('/sisters/<int:version>', methods=['GET'])
def get_sisters_by_year(version):
    """Get servers of specific version, running on the same machine"""
    return [x.get_cache_data() for x in serverinfo.get_registered_servers()
            if int(x.version) == version]
