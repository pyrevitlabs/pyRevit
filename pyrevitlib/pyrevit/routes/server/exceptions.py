# -*- coding: utf-8 -*-
"""Route custom exceptions."""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import HOST_APP


class ServerException(Exception):
    """Server error."""
    def __init__(self, message, exception_type, exception_traceback):
        message = "Server error (%s): %s\n%s\n" % (
            exception_type.__name__ if exception_type else "",
            message,
            exception_traceback
        )
        super(ServerException, self).__init__(message)
        self.status = 500 # https://httpstatuses.com/500


class APINotDefinedException(Exception):
    """API is not defined exception."""
    def __init__(self, api_name):
        message = "API is not defined: \"%s\"" % api_name
        super(APINotDefinedException, self).__init__(message)
        self.status = 404 # https://httpstatuses.com/404


class RouteHandlerNotDefinedException(Exception):
    """Route does not exits exception."""
    def __init__(self, api_name, route, method):
        message = \
        "Route does not exits: \"%s %s%s\"" % (method, api_name, route)
        super(RouteHandlerNotDefinedException, self).__init__(message)
        self.status = 404 # https://httpstatuses.com/404


class RouteHandlerDeniedException(Exception):
    """Route handler was denied by host."""
    def __init__(self, request):
        message = "Route handler was denied by host: \"%s\"" % request.route
        super(RouteHandlerDeniedException, self).__init__(message)
        self.status = 406 # https://httpstatuses.com/406
        self.source = HOST_APP.pretty_name


class RouteHandlerTimedOutException(Exception):
    """Route handler was timed out by host."""
    def __init__(self, request):
        message = "Route handler was timed out by host: \"%s\"" % request.route
        super(RouteHandlerTimedOutException, self).__init__(message)
        self.status = 408 # https://httpstatuses.com/408
        self.source = HOST_APP.pretty_name


class RouteHandlerIsNotCallableException(Exception):
    """Route handler is not callable."""
    def __init__(self, hndlr_name):
        message = "Route handler is not callable: \"%s\"" % hndlr_name
        super(RouteHandlerIsNotCallableException, self).__init__(message)
        self.status = 405 # https://httpstatuses.com/405
        self.source = HOST_APP.pretty_name


class RouteHandlerExecException(Exception):
    """Route handler exception."""
    def __init__(self, message):
        message = "Route exception in Execute: %s" % message
        super(RouteHandlerExecException, self).__init__(message)
        self.status = 408 # https://httpstatuses.com/408
        self.source = HOST_APP.pretty_name


class RouteHandlerException(Exception):
    """Route handler exception."""
    def __init__(self,
                 message, exception_type, exception_traceback,
                 clsx_message, clsx_source, clsx_stacktrace, clsx_targetsite):
        message = "%s: %s\n%s\n" \
                  "Script Executor Traceback:\n" \
                  "%s: %s\n%s\n%s" % (
                      exception_type.__name__ if exception_type else "",
                      message,
                      exception_traceback,
                      clsx_source,
                      clsx_message,
                      clsx_stacktrace,
                      clsx_targetsite
                  )
        super(RouteHandlerException, self).__init__(message)
        self.status = 408 # https://httpstatuses.com/408
        self.source = HOST_APP.pretty_name
