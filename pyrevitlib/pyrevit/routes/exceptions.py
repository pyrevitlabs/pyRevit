"""Route custom exceptions"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import HOST_APP


class APINotDefinedException(Exception):
    """API is not defined exception"""
    def __init__(self, api_name):
        message = "API is not defined: \"%s\"" % api_name
        super(APINotDefinedException, self).__init__(message)
        self.status = 404 # https://httpstatuses.com/404
        self.source = "pyrevit routes server"


class RouteHandlerNotDefinedException(Exception):
    """Route does not exits exception"""
    def __init__(self, api_name, route, method):
        message = \
        "Route does not exits: \"%s %s/%s\"" % (method, api_name, route)
        super(RouteHandlerNotDefinedException, self).__init__(message)
        self.status = 404 # https://httpstatuses.com/404
        self.source = "pyrevit routes server"


class RouteHandlerDeniedException(Exception):
    """Route handler was denied by host"""
    def __init__(self, request):
        message = "Route handler was denied by host: \"%s\"" % request.route
        super(RouteHandlerDeniedException, self).__init__(message)
        self.status = 406 # https://httpstatuses.com/406
        self.source = HOST_APP.pretty_name


class RouteHandlerTimedOutException(Exception):
    """Route handler was timed out by host"""
    def __init__(self, request):
        message = "Route handler was timed out by host: \"%s\"" % request.route
        super(RouteHandlerTimedOutException, self).__init__(message)
        self.status = 408 # https://httpstatuses.com/408
        self.source = HOST_APP.pretty_name
