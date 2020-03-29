"""pyRevit core startup script"""
#pylint: disable=import-error,invalid-name,broad-except,unused-argument
from pyrevit import HOST_APP
from pyrevit import routes
from pyrevit.loader import sessioninfo
from pyrevit.loader import sessionmgr
from pyrevit.userconfig import user_config


# define core api =============================================================


api = routes.API("pyrevit-core")


@api.route('/configs/ports/', methods=['GET'])
def get_server_configs(request, uiapp):
    """Get server port configs"""
    return user_config.core.get_option("routes_ports", default_value={})


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


# =============================================================================
