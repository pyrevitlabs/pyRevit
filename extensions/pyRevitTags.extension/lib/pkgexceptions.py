"""Package module exceptions."""
#pylint: disable=E0401
from pyrevit import PyRevitException


class HistoryStartedAfter(PyRevitException):
    pass


class HistoryEndedBefore(PyRevitException):
    pass


class HistoryStartedBefore(PyRevitException):
    pass


class HistoryEndedAfter(PyRevitException):
    pass


class HistoryStartMustBeFirst(PyRevitException):
    pass


class HistoryEndMustBeLast(PyRevitException):
    pass


class ReadOnlyStart(PyRevitException):
    pass


class ReadOnlyEnd(PyRevitException):
    pass


class ReadOnlyCommitInHistory(PyRevitException):
    pass


class CanNotRemoveStart(PyRevitException):
    pass


class CanNotUnsetNonExisting(PyRevitException):
    pass
