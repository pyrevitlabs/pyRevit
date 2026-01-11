# -*- coding: utf-8 -*-
"""HTTP API framework similar to flask."""
# types to be exported
#pylint: disable=wildcard-import,redefined-outer-name,unused-variable
#pylint: disable=dangerous-default-value,invalid-name
from pyrevit.routes.server import *


class API(object):
    """API root object.

    Args:
        name (str): URL-safe unique root name of the API

    Examples:
        ```python
        from pyrevit import routes
        api = routes.API("pyrevit-core")
        @api.route('/sessions/', methods=['POST'])
        def reload_pyrevit(uiapp):
            new_session_id = sessionmgr.reload_pyrevit()
            return {"session_id": new_session_id}
        ```
    """
    def __init__(self, name):
        self.name = name

    def route(self, pattern, methods=['GET']):
        """Define a new route on this API."""
        def __func_wrapper__(f):
            for method in methods:
                add_route(
                    api_name=self.name,
                    pattern=pattern,
                    method=method,
                    handler_func=f
                    )
            return f
        return __func_wrapper__



def active_routes_api():
    """Activates routes API."""
    from pyrevit.routes import api
