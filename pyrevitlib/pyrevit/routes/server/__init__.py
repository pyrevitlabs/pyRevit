
# -*- coding: utf-8 -*-
"""Handles http api routing and serving with usage similar to flask."""
#pylint: disable=import-error,invalid-name,broad-except,dangerous-default-value,missing-docstring
from pyrevit import HOST_APP, PyRevitException
from pyrevit.api import DB, UI
from pyrevit.labs import TargetApps
from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config
from pyrevit.loader import sessioninfo

# types to be exported
from pyrevit.routes.server.base import \
    OK, ACCEPTED, INTERNAL_SERVER_ERROR, NO_CONTENT
from pyrevit.routes.server.base import Request, Response

from pyrevit.routes.server import serverinfo
from pyrevit.routes.server import router
from pyrevit.routes.server import server


__all__ = (
    'OK', 'ACCEPTED', 'INTERNAL_SERVER_ERROR', 'NO_CONTENT',
    'Request', 'Response',
    'init', 'activate_server', 'deactivate_server', 'get_active_server',
    'make_response', 'get_routes', 'add_route', 'remove_route',
    )


mlogger = get_logger(__name__)


def init():
    """Initialize routes. Reset all registered routes and shutdown servers."""
    # clear all routes
    router.reset_routes()
    # stop existing server
    deactivate_server()


def activate_server():
    """Activate routes server for this host instance."""
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
            return routes_server
        except Exception as rs_ex:
            serverinfo.unregister()
            mlogger.error("Error starting Routes server | %s", str(rs_ex))


def deactivate_server():
    """Deactivate the active routes server for this host instance."""
    routes_server = envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    if routes_server:
        try:
            routes_server.stop()
            envvars.set_pyrevit_env_var(envvars.ROUTES_SERVER, None)
            serverinfo.unregister()
        except Exception as rs_ex:
            mlogger.error("Error stopping Routes server | %s", str(rs_ex))


def get_active_server():
    """Get active routes server for this host instance."""
    return envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)


def make_response(data, status=OK, headers=None):
    """Create Reponse object with."""
    res = Response(status=status, data=data)
    for key, value in (headers or {}).items():
        res.add_header(key, value)
    return res


def get_routes(api_name):
    """Get all registered routes for given API name.

    Args:
        api_name (str): unique name of the api
    """
    return router.get_routes(api_name)


def add_route(api_name, pattern, method, handler_func):
    """Add new route for given API name.

    Args:
        api_name (str): unique name of the api
        pattern (str): route pattern
        method (str): method name
        handler_func (function): route handler function
    """
    return router.add_route(api_name, pattern, method, handler_func)


def remove_route(api_name, pattern, method):
    """Remove previously registered route for given API name.

    Args:
        api_name (str): unique name of the api
        pattern (str): route pattern
        method (str): method name
    """
    return router.remove_route(api_name, pattern, method)
