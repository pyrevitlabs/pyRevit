"""Route dictionary"""
#pylint: disable=import-error,invalid-name,broad-except
from collections import namedtuple

from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


Route = namedtuple('Route', ['route', 'verb'])


def get_routes(api_name):
    """Add a new root route for given API name

    Args:
        api_name (str): unique name of the api
    """
    if api_name is None:
        raise Exception("API name can not be None.")

    routes_map = envvars.get_pyrevit_env_var(envvars.ROUTES_ROUTES)
    if routes_map is None:
        routes_map = {}
        envvars.set_pyrevit_env_var(envvars.ROUTES_ROUTES, routes_map)

    if api_name in routes_map:
        return routes_map[api_name]
    else:
        app_routes = {}
        routes_map[api_name] = app_routes
        return app_routes


def get_route(api_name, route, method):
    """Return defined route:method for given API name

    Args:
        api_name (str): unique name of the api
        route (str): route string
        method (str): method name
    """
    route = Route(route=route, verb=method)
    app_routes = get_routes(api_name)
    if app_routes:
        return app_routes.get(route, None)


def add_route(api_name, route, method, handler_func):
    """Add new route for given API name

    Args:
        api_name (str): unique name of the api
        route (str): route string
        method (str): method name
        handler_func (function): route handler function
    """
    route = Route(route=route, verb=method)
    app_routes = get_routes(api_name)
    app_routes[route] = handler_func


def remove_route(api_name, route, method):
    """Remove prevriously defined route for given API name

    Args:
        api_name (str): unique name of the api
        route (str): route string
        method (str): method name
    """
    route = Route(route=route, verb=method)
    app_routes = get_routes(api_name)
    app_routes.pop(route)
