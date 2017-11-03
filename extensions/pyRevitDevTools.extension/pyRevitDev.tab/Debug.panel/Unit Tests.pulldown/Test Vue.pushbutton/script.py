from pyrevit import revit, DB
from pyrevit import output, script


@output.route('/selectall')
def selectall():
    print('dfdfdf')


output.load_index(script.get_bundle_file('index.html'))
