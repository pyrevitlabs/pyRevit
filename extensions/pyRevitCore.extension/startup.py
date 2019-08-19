"""pyRevit core startup script."""
#pylint: disable=import-error,invalid-name,broad-except,unused-argument
from pyrevit import routes
from pyrevit.loader import sessionmgr

api = routes.API("pyrevit-core")

@api.route('/sessions/', methods=['POST'])
def reload_pyrevit(uiapp):
    """POST /sessions/ will reload pyRevit."""
    new_session_id = sessionmgr.reload_pyrevit()
    return {"session_id": new_session_id}
