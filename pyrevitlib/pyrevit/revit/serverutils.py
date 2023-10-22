"""Helper functions for working with revit server."""

from collections import namedtuple
from pyrevit.framework import sqlite3

from pyrevit import DB


MODEL_HISTORY_SQLDB = '/Data/Model.db3'


SyncHistory = namedtuple('SyncHistory', ['index',
                                         'userid',
                                         'timestamp'])
"""namedtuple for model sync history data in revit server

Attributes:
    index (int): row index in history db
    userid (str): user identifier
    timestamp (str): time stamp string (e.g. "2017-12-13 19:56:20")
"""


def get_server_path(doc, path_dict):
    """Return file path of a model hosted on revit server.

    Args:
        doc (Document): revit document object
        path_dict (dict): dict of RSN paths and their directory paths

    Examples:
        ```python
        rsn_paths = {'RSN://SERVERNAME': '//servername/filestore'}
        get_server_path(doc, rsn_paths)
        ```
        "//servername/filestore/path/to/model.rvt"
    """
    model_path = doc.GetWorksharingCentralModelPath()
    path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path)
    for key, value in path_dict.items():
        path = path.replace(key, value)

    return path


def get_model_sync_history(server_path):
    """Read model sync history from revit server sqlite history file.

    Args:
        server_path (str): directory path of revit server filestore

    Returns:
        (list[SyncHistory]): list of SyncHistory instances

    Examples:
        ```python
        get_model_sync_history("//servername/path/to/model.rvt")
        ```
        [SyncHistory(index=498, userid="user",
                    timestamp="2017-12-13 19:56:20")]
    """
    db_path = server_path + MODEL_HISTORY_SQLDB
    conn = sqlite3.connect(db_path)
    sync_hist = []
    for row in conn.execute("SELECT * FROM ModelHistory"):
        sync_hist.append(SyncHistory(index=int(row[0]),
                                     userid=row[1],
                                     timestamp=row[2][:-1]))
    return sync_hist
