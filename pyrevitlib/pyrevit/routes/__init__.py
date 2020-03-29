"""Handles http api routing and serving with usage similar to flask."""
#pylint: disable=import-error,invalid-name,broad-except,dangerous-default-value,missing-docstring
from pyrevit import HOST_APP, PyRevitException
from pyrevit.api import DB, UI
from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config

from pyrevit.routes import router
from pyrevit.routes import server
from pyrevit.routes.server import Request, Response


__all__ = ('API', 'Request', 'Response',
           'activate_routes', 'deactivate_routes')


mlogger = get_logger(__name__)


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

    def route(self, route_url, methods=['GET']):
        """Define a new route on this API."""
        def __func_wrapper__(f):
            for method in methods:
                router.add_route(
                    api_name=self.name,
                    route=route_url,
                    method=method,
                    handler_func=f
                    )
            return f
        return __func_wrapper__


def activate_routes():
    routes_server = envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    if not routes_server:
        host = user_config.core.get_option("routes_host", default_value='')
        ports_dict = \
            user_config.core.get_option("routes_ports", default_value={})
        port = ports_dict.get(HOST_APP.version, None)
        if port:
            routes_server = server.RoutesServer(ip=host, port=port)
            envvars.set_pyrevit_env_var(envvars.ROUTES_SERVER, routes_server)
            routes_server.start()
        else:
            mlogger.error("Port is not configured for Routes server")


def deactivate_routes():
    routes_server = envvars.get_pyrevit_env_var(envvars.ROUTES_SERVER)
    if routes_server:
        envvars.set_pyrevit_env_var(envvars.ROUTES_SERVER, None)
        routes_server.stop()
