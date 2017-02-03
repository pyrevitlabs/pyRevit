import json

from pyrevit import HOST_APP

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, View
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


doc = HOST_APP.uiapp.ActiveUIDocument.Document
uidoc = HOST_APP.uiapp.ActiveUIDocument


DEFAULT_LINK = '<a style="background-color: #f5f7f2; ' \
                         'color: #649417; ' \
                         'border: 1px solid #649417; ' \
                         'vertical-align:middle;margin:-4,0,-4,0; ' \
                         'margin: 2px; ' \
                         'padding: 2px 6px; ' \
                         'text-align: center; ' \
                         'text-decoration: none; ' \
                         'display: inline-block;" href="{}{}">{}</a>'
PROTOCOL_NAME =  'revit://'
COMMAND_KEY = 'command'
DATA_KEY = 'data'


class ProtocolCommandTypes:
    SELECT = 'select'


class GenericProtocolCommand(object):
    type_id = None

    def __init__(self, args):
        self._args = args

    @property
    def url_data(self):
        return json.dumps({COMMAND_KEY: self.type_id, DATA_KEY: self.get_elements()}, separators=(',', ':'))

    @property
    def url_title(self):
        title_str = str(self.get_elements())
        title_str = title_str.replace('[', '').replace(']', '')
        return title_str


class SelectElementsCommand(GenericProtocolCommand):
    type_id = ProtocolCommandTypes.SELECT

    def get_elements(self):
        return [arg.IntegerValue for arg in self._args if isinstance(arg, ElementId)]

    def execute(self):
        el_list = List[ElementId]()
        for arg in self._args:
            if type(arg) == int:
                el_list.Add(ElementId(arg))

        uidoc.Selection.SetElementIds(el_list)

        for ei_id in el_list:
            try:
                el = doc.GetElement(ei_id)
                if isinstance(el, View):
                    uidoc.ActiveView = el
                else:
                    uidoc.ActiveView = doc.GetElement(el.OwnerViewId)
            except Exception as err:
                print(err)


def _get_command_from_arg(cmd_args):
    return SelectElementsCommand(cmd_args)


def _get_command_from_data(cmd_data):
    cmd_dict = json.loads(cmd_data)
    if cmd_dict[COMMAND_KEY] == ProtocolCommandTypes.SELECT:
        return SelectElementsCommand(cmd_dict[DATA_KEY])


def _make_protocol_url(url_data, url_title):
    return DEFAULT_LINK.format(PROTOCOL_NAME, url_data.replace('\"','\''), url_title)


def make_url(args):
    cmd = _get_command_from_arg(args)
    return _make_protocol_url(cmd.url_data, cmd.url_title)


def process_url(url_data):
    cmd = _get_command_from_data(url_data)
    return cmd.execute()
