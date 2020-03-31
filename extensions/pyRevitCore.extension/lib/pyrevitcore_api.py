#pylint: disable=import-error,invalid-name,broad-except,unused-argument
from pyrevit import HOST_APP
from pyrevit import routes
from pyrevit.loader import sessioninfo
from pyrevit.loader import sessionmgr


api = routes.API("pyrevit-core")


@api.route('/servers/', methods=['GET'])
def get_servers(request, uiapp):
    """Get server port configs"""
    return routes.get_available_servers()


@api.route('/status', methods=['GET'])
def get_status(request, uiapp):
    """Get current session status"""
    return {
        "host": HOST_APP.pretty_name,
        "username": HOST_APP.username,
        "session_id": sessioninfo.get_session_uuid(),
        }


@api.route('/revits/', methods=['GET'])
def get_revits(request, uiapp):
    # TODO: get all instances of revit
    pass


@api.route('/sessions/', methods=['POST'])
def reload_pyrevit(request, uiapp):
    """Reload pyRevit"""
    new_session_id = sessionmgr.reload_pyrevit()
    return {"session_id": new_session_id}
