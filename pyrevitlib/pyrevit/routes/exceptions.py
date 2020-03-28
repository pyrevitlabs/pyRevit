class APINotDefinedException(Exception):
    def __init__(self):
        message = "API is not defined"
        super(APINotDefinedException, self).__init__(message)


class RouteHandlerNotDefinedException(Exception):
    def __init__(self):
        message = "Route does not exits"
        super(RouteHandlerNotDefinedException, self).__init__(message)
