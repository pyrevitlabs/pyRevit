"""Revit-aware event handler"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.routes import router


mlogger = get_logger(__name__)


class RequestHandler(UI.IExternalEventHandler):
    """Revit external event handler type."""
    name = None
    route = None
    method = None
    data = None
    res_code = 200
    res_data = None

    def Execute(self, uiapp):
        """This method is called to handle the external event."""
        route_handler = router.get_route(
            api_name=self.name,
            route=self.route,
            method=self.method
            )
        if route_handler:
            try:
                self.res_data = route_handler(uiapp)
                self.res_code = 200
            except Exception as ex:
                self.res_code = 500
                self.res_data = {"exception": str(ex)}
        else:
            self.res_code = 404

    def GetName(self):
        """String identification of the event handler."""
        return self.name
