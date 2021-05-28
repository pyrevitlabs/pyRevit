"""Testing startup stuff"""
#pylint: disable=import-error,invalid-name,broad-except,unused-argument
from pyrevit import routes
from pyrevit.loader import sessionmgr
from pyrevit.labs import TargetApps


api = routes.API('pyrevit-core')


# TODO: auth
@api.route('/sessions/', methods=['POST'])
def reload_pyrevit(uiapp):
    """Reload pyRevit"""
    new_session_id = sessionmgr.reload_pyrevit()
    return {"session_id": new_session_id}


# pyrevit related api
# TODO: configuration
# TODO: attachments
# TODO: ...
