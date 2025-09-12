# -*- coding: utf-8 -*-
"""Route dictionary."""
#pylint: disable=import-error,invalid-name,broad-except
import re
import uuid
from collections import namedtuple

from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger

from pyrevit.routes.server import handler


mlogger = get_logger(__name__)


ROUTE_VAR_SEP = ':'


Route = namedtuple('Route', ['pattern', 'method'])

RouteParam = namedtuple('RouteParam', ['key', 'value'])


def _make_finder_pattern(route_pattern):
    modified_pattern = re.sub(r"\<.+?\>", "(.+)", route_pattern)
    return '^%s$' % modified_pattern


def _find_pattern_keys(route_pattern):
    return re.findall(r"\<(.+?)\>", route_pattern)


def _find_pattern_values(finder_pattern, path):
    values = re.findall(finder_pattern, path)
    if values:
        # if more that one match, it returns a tuple
        if isinstance(values[0], tuple):
            return [x for x in values[0]]
        return values


def _extract_route_param_keys(route_pattern):
    clean_keys = set()
    for param_key in _find_pattern_keys(route_pattern):
        if ROUTE_VAR_SEP in param_key:
            clean_keys.add(param_key.split(ROUTE_VAR_SEP)[1])
        else:
            clean_keys.add(param_key)
    return clean_keys


def _validate_pattern(route_pattern):
    param_keys = _extract_route_param_keys(route_pattern)
    return not param_keys.intersection(handler.RESERVED_VAR_NAMES)


def _cast_value(cast, val):
    if cast in ['int', 'float', 'double', 'bool']:
        return eval('%s(%s)' % (cast, val)) #pylint: disable=eval-used
    elif cast == 'uuid':
        return uuid.UUID(val)


def route_match(route, path, method):
    """Test if route pattern matches given request path."""
    finder_pattern = _make_finder_pattern(route.pattern)
    # if same method and matching pattern
    if route.method == method \
            and re.match(finder_pattern, path):
        # check variable data types
        # e.g. paths below are different
        # api/v1/posts/<int:pid> matches
        #     api/v1/posts/12
        # api/v1/posts/<int:pid> does not match
        #     api/v1/posts/661a4f7a-7377-11ea-9494-acde48001122
        for key, val in zip(
                _find_pattern_keys(route.pattern),
                _find_pattern_values(finder_pattern, path)
            ):
            if ROUTE_VAR_SEP in key:
                cast, key = key.split(ROUTE_VAR_SEP)
                try:
                    val = _cast_value(cast, val)
                except Exception:
                    # if any of variable types does not match, say no
                    return False
        # if all variable types matched, say yes
        return True
    # otherwise say no
    return False


def extract_route_params(route_pattern, request_path):
    """Extracts route params from request path based on pattern.

    Examples:
        ```python
        extract_route_params('api/v1/posts/<int:id>', 'api/v1/posts/12')
        ```
        [<RouteParam key:id value=12>]
    """
    finder_pattern = _make_finder_pattern(route_pattern)
    route_params = []
    for key, val in zip(
            _find_pattern_keys(route_pattern),
            _find_pattern_values(finder_pattern, request_path)
        ):
        if ROUTE_VAR_SEP in key:
            cast, key = key.split(ROUTE_VAR_SEP)
            try:
                val = _cast_value(cast, val)
            except Exception as cast_ex:
                mlogger.debug(
                    'Cast error %s -> %s | %s', val, cast, str(cast_ex)
                    )
        route_params.append(
            RouteParam(key=key, value=val)
        )
    return route_params


def reset_routes():
    """Reset registered APIs and routes."""
    envvars.set_pyrevit_env_var(envvars.ROUTES_ROUTES, {})


def get_routes(api_name):
    """Get all registered routes for given API name.

    Args:
        api_name (str): unique name of the api

    Returns:
        (dict[str, Caller[]]): registered routes
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


def get_route_handler(api_name, path, method):
    """Return registered handler for given API, path, and method.

    Args:
        api_name (str): unique name of the api
        path (str): request path
        method (str): method name

    Returns:
        api_route (Route): API route
        route_handler (Caller): registered route handler function
    """
    for api_route, route_handler in get_routes(api_name).items():
        if route_match(api_route, path, method):
            return api_route, route_handler
    return None, None


def add_route(api_name, pattern, method, handler_func):
    """Add new route for given API name.

    Args:
        api_name (str): unique name of the api
        pattern (str): route pattern
        method (str): method name
        handler_func (function): route handler function
    """
    if _validate_pattern(pattern):
        route = Route(pattern=pattern, method=method)
        app_routes = get_routes(api_name)
        app_routes[route] = handler_func
    else:
        mlogger.error('Route pattern is invalid: %s', pattern)


def remove_route(api_name, pattern, method):
    """Remove prevriously defined route for given API name.

    Args:
        api_name (str): unique name of the api
        pattern (str): route pattern
        method (str): method name
    """
    route = Route(pattern=pattern, method=method)
    app_routes = get_routes(api_name)
    app_routes.pop(route)
