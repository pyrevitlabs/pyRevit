"""Handles http api routing and serving with usage similar to flask."""
#pylint: disable=import-error,invalid-name,broad-except,dangerous-default-value,missing-docstring
from pyrevit import HOST_APP, PyRevitException
from pyrevit.api import DB, UI
from pyrevit.labs import TargetApps
from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config
from pyrevit.loader import sessioninfo

from pyrevit.routes import router
from pyrevit.routes import server
from pyrevit.routes import serverinfo

# types to be exported
from pyrevit.routes.base import Request, Response, make_response
from pyrevit.routes.api import API


__all__ = ('API', 'Request', 'Response', 'make_response',
           'activate_server', 'deactivate_server')


mlogger = get_logger(__name__)


REVITCTRL = TargetApps.Revit.RevitController


PYREVIT_ROUTES_API = API('routes')


def init():
    """Initialize routes. Reset all registered routes and shutdown servers"""
    # clear all routes
    router.reset_routes()
    # stop existing server
    deactivate_server()


def activate_server():
    """Activate routes server for this host instance"""
    routes_server = envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    if not routes_server:
        try:
            rsinfo = serverinfo.register()
            routes_server = \
                server.RoutesServer(
                    host=rsinfo.server_host,
                    port=rsinfo.server_port
                    )
            routes_server.start()
            envvars.set_pyrevit_env_var(envvars.ROUTES_SERVER, routes_server)
        except Exception as rs_ex:
            serverinfo.unregister()
            mlogger.error("Error starting Routes server | %s", str(rs_ex))


def deactivate_server():
    """Deactivate the active routes server for this host instance"""
    routes_server = envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    if routes_server:
        try:
            routes_server.stop()
            envvars.set_pyrevit_env_var(envvars.ROUTES_SERVER, None)
            serverinfo.unregister()
        except Exception as rs_ex:
            mlogger.error("Error stopping Routes server | %s", str(rs_ex))


def get_active_server():
    """Get active routes server for this host instance"""
    return envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)


# =============================================================================
# routes server base API
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
