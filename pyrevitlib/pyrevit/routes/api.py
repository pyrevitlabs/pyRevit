# -*- coding: utf-8 -*-
"""Builtin routes API.

This module also provides the API object to be used by third-party
api developers to define new apis
"""
#pylint: disable=invalid-name
from pyrevit import HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader import sessioninfo

from pyrevit import routes
from pyrevit.routes.server import serverinfo


mlogger = get_logger(__name__)


# =============================================================================
# routes server base API
routes_api = routes.API('routes')
# =============================================================================


# GET /status
@routes_api.route('/status', methods=['GET'])
def get_status():
    """Get server status."""
    return {
        "host": HOST_APP.pretty_name,
        "username": HOST_APP.username,
        "session_id": sessioninfo.get_session_uuid(),
        }

# GET /sisters
@routes_api.route('/sisters', methods=['GET'])
def get_sisters():
    """Get other servers running on the same machine."""
    return [x.get_cache_data() for x in serverinfo.get_registered_servers()]


# GET /sisters/<int:year>
@routes_api.route('/sisters/<int:version>', methods=['GET'])
def get_sisters_by_year(version):
    """Get servers of specific version, running on the same machine."""
    return [x.get_cache_data() for x in serverinfo.get_registered_servers()
            if int(x.version) == version]
