# Revit server execeptions -----------------------------------------------------
class ServerVersionNotSupported(Exception):
    pass


class ServerConnectionError(Exception):
    pass


class ServerTimeoutError(Exception):
    pass


class UnhandledException(Exception):
    pass


# Revit Server API http status codes  ------------------------------------------
# 400
class ServerBadRequestError(Exception):
    pass


# 403
class ServerForbiddenError(Exception):
    pass


# 404
class ServerFileNotFound(Exception):
    pass


# 405
class ServerMethodNotAllowedError(Exception):
    pass


# 414
class ServerURITooLongError(Exception):
    pass


# 500
class ServerInternalError(Exception):
    pass


# 501
class ServerNotImplemented(Exception):
    pass


# 503
class ServerServiceUnavailableError(Exception):
    pass
