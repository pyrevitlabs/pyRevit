import json

from pyrevit import HOST_APP
from pyrevit.coreutils import prepare_html_str

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.UI import TaskDialog

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
        HOST_APP.uiapp.ActiveUIDocument.Selection.SetElementIds(el_list)


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
    return prepare_html_str(_make_protocol_url(cmd.url_data, cmd.url_title))


def process_url(url):
    try:
        if PROTOCOL_NAME in url:
            url_data = url.split(PROTOCOL_NAME)[1]
            url_data = url_data.replace('/', '').replace('\'','\"')
            cmd = _get_command_from_data(url_data)
            cmd.execute()
    except Exception as exec_err:
        logger.error('Error handling link | {}'.format(exec_err))
