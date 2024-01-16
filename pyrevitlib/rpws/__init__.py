r"""Python wrapper for Autodesk Revit Server.

This is a python module for interacting with Autodesk Revit Server using
its RESTful API. This module requires 'requests' module for handling http
requests to the Revit Server.

Module Files:
    exceptions.py: Defines module exceptions and custom exceptions for
                   http status codes returned by the server

    api.py: Documents all standard keys that are returned in JSON
            dictionaries from server API calls.

    models.py: Defines classes and namedtuples that wrap the data
               returned from server API calls.

    server.py: Defines the server wrapper class. RevitServer class aims to
               support all the Revit Server API functionality.

Example:
    >>> name = '<server name>'
    >>> version = '2017'    # server version in XXXX format
    >>> rserver = RevitServer(name, version)
    >>> # listing all files, folders, and models in a server
    >>> for parent, folders, files, models in rserver.walk():
    ...     print(parent)
    ...     for fd in folders:
    ...         print('\t@d {}'.format(fd.path))
    ...     for f in files:
    ...         print('\t@f {}'.format(f.path))
    ...     for m in models:
    ...         print('\t@m {}'.format(m.path))

"""


__version__ = "1.1.0"


from rpws.exceptions import *
from rpws.server import RevitServer
