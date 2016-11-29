import sys
import traceback


TRACEBACK_TITLE = '<strong>Traceback:</strong>'


# General Exceptions
class PyRevitException(Exception):
    """Base class for all pyRevit Exceptions.
    Parameters args and message are derived from Exception class.
    """
    def __str__(self):
        sys.exc_type, sys.exc_value, sys.exc_traceback = sys.exc_info()
        tb_report = traceback.format_tb(sys.exc_traceback)[0]
        if self.args:
            message = self.args[0]
            return '{}\n\n{}\n{}'.format(message, TRACEBACK_TITLE, tb_report)
        else:
            return '{}\n{}'.format(TRACEBACK_TITLE, tb_report)


class PyRevitIOError(PyRevitException):
    pass
