"""Module exceptions."""


# Revit server execeptions ----------------------------------------------------
class ServerVersionNotSupported(Exception):
    """Server version not supported exception."""

    pass


class ServerConnectionError(Exception):
    """Server connection exception."""

    pass


class ServerTimeoutError(Exception):
    """Server timeout error."""

    pass


class UnhandledException(Exception):
    """General exception for any unhandled exceptions."""

    pass


# Revit Server API http status codes  -----------------------------------------
# 400
class ServerBadRequestError(Exception):
    """Server bad request error."""

    pass


# 403
class ServerForbiddenError(Exception):
    """Server forbidden command error."""

    pass


# 404
class ServerFileNotFound(Exception):
    """Server file or folder not found error."""

    pass


# 405
class ServerMethodNotAllowedError(Exception):
    """Server method not allowed error."""

    pass


# 414
class ServerURITooLongError(Exception):
    """Server uri too long error."""

    pass


# 500
class ServerInternalError(Exception):
    """Server internal error."""

    pass


# 501
class ServerNotImplemented(Exception):
    """Server not implemented error."""

    pass


# 503
class ServerServiceUnavailableError(Exception):
    """Server service unavailable error."""

    pass
