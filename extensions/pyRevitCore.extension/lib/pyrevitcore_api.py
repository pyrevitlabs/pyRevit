#pylint: disable=import-error,invalid-name,broad-except,unused-argument
from pyrevit import HOST_APP
from pyrevit import routes
from pyrevit.loader import sessioninfo
from pyrevit.loader import sessionmgr


api = routes.API("pyrevit-core")


@api.route('/servers/')
def get_servers():
    """Get server port configs"""
    return routes.get_available_servers()


@api.route('/status')
def get_status():
    """Get current session status"""
    return {
        "host": HOST_APP.pretty_name,
        "username": HOST_APP.username,
        "session_id": sessioninfo.get_session_uuid(),
        }


@api.route('/revits/')
def get_revits():
    # TODO: get all instances of revit
    pass


# if has uiapp arg, it will be executed in api context
@api.route('/sessions/', methods=['POST'])
def reload_pyrevit(uiapp):
    """Reload pyRevit"""
    new_session_id = sessionmgr.reload_pyrevit()
    return {"session_id": new_session_id}
