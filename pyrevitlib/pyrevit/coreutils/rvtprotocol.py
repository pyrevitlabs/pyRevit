import re
import json

from pyrevit import HOST_APP

from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId


PROTOCOL_NAME: 'revit:'


class ProtocolCommand:
    def __init__(self, args):
        self._args = args

    @propery
    def url_data(self):
        json.dumps(self, default=lambda o: o.get_data(), sort_keys=True, indent=4)

    def get_data(self):
        return {"select":[self._arg]}

    def execute():
        id_finder = re.compile('\d+')
        el_id = int(id_finder.findall(url)[0])
        HOST_APP.uiapp.ActiveUIDocument.Selection.SetElementIds(List[ElementId](el_id))


def get_command_from_arg(args):
    return ProtocolCommand(args)


def make_url(*args):
    return prepare_html_str('<a href="{}:{}">{}</a>'.format(PROTOCOL_NAME,
                                                            get_command_from_arg(args).url_data,
                                                            args))


def process_url(url):
    if url.startswith(PROTOCOL_NAME):
        cmd = ProtocolCommand.from_data(url.replace(PROTOCOL_NAME, ''))
        cmd.execute()
