"""Testing startup stuff"""
#pylint: disable=import-error,invalid-name,broad-except,unused-argument
from pyrevit import HOST_APP
from pyrevit import routes
from pyrevit.loader import sessioninfo
from pyrevit.loader import sessionmgr
from pyrevit.labs import TargetApps


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
    """Get running instances of Revit"""
    return routes.make_response(
        data=[
            {
                "pid": x.ProcessId,
                "name": x.RevitProduct.Name,
                "version": str(x.RevitProduct.Version),
                "build_number": x.RevitProduct.BuildNumber,
                "build_target": x.RevitProduct.BuildTarget,
                "language_code": x.RevitProduct.LanguageCode,
                "install_path": x.RevitProduct.InstallLocation,
            } for x in
            TargetApps.Revit.RevitController.ListRunningRevits()
        ]
    )


# if has uiapp arg, it will be executed in api context
@api.route('/sessions/', methods=['POST'])
def reload_pyrevit(uiapp):
    """Reload pyRevit"""
    new_session_id = sessionmgr.reload_pyrevit()
    return {"session_id": new_session_id}
