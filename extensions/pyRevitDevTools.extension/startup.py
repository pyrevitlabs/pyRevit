"""Example of IronPython script to be executed by pyRevit on extension load

The script filename must end in startup.py

To Test:
- rename file to startup.py
- reload pyRevit: pyRevit will run this script after successfully
  created the DLL for the extension.

pyRevit runs the startup script in a dedicated IronPython engine and output
window. Thus the startup script is isolated and can not hurt the load process.
All errors will be printed to the dedicated output window similar to the way
errors are printed from pyRevit commands.
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
#pylint: disable=unused-import,wrong-import-position,unused-argument
#pylint: disable=missing-docstring
import sys

from pyrevit import HOST_APP, framework
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import routes


# add your module paths to the sys.path here
# sys.path.append(r'path/to/your/module')

print('Startup script execution test.')
print('\n'.join(sys.path))

# test imports from same directory and exensions lib
import startuplibimport
print('lib/ import works in startup.py')


# test code for creating event handlers =======================================
# define event handler
def docopen_eventhandler(sender, args):
    forms.alert('Document Opened: {}'.format(args.PathName))

# add to DocumentOpening
# type is EventHandler[DocumentOpeningEventArgs] so create that correctly
HOST_APP.app.DocumentOpening += \
    framework.EventHandler[DB.Events.DocumentOpeningEventArgs](
        docopen_eventhandler
        )


# test code routes module =====================================================

api = routes.API("pyrevit-dev")


@api.route('/forms-block', methods=['POST'])
def forms_blocking(request, uiapp):
    """Test blocking GUI"""
    forms.alert("Routes works!")
    return 'Routes works!'


@api.route('/doors/', methods=['GET'])
def get_doors(request, uiapp):
    """Test API access: find doors in active model"""
    doors = revit.query.get_elements_by_categories(
        [DB.BuiltInCategory.OST_Doors]
        )
    doors_data = [x.Id.IntegerValue for x in doors]
    return routes.Response(status=202, data=doors_data)


@api.route('/except', methods=['GET'])
def raise_except(request, uiapp):
    """Test handler exception"""
    m = 12 / 0


@api.route('/reflect', methods=['POST'])
def reflect_request(request, uiapp):
    return {
        "name": request.name,
        "route": request.route,
        "method": request.method,
        "data": request.data
    }
