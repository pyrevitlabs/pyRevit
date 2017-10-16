import json

from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit.revit import DB, UI
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


PROTOCOL_NAME = 'revit://'
COMMAND_KEY = 'command'
DATA_KEY = 'data'


DEFAULT_LINK = '<a title="Click to select or show element" ' \
               'style="background-color: #f5f7f2; ' \
               'font-size:8pt; ' \
               'color: #649417; ' \
               'border: 1px solid #649417; ' \
               'border-radius:3px; ' \
               'vertical-align:middle; '\
               'margin:-4,0,-4,0; ' \
               'margin: 2px; ' \
               'padding: 1px 4px; ' \
               'text-align: center; ' \
               'text-decoration: none; ' \
               'display: inline-block;" href="{}{}">{}</a>'


# noinspection PyClassHasNoInit
class ProtocolCommandTypes:
    SELECT = 'select'


class GenericProtocolCommand(object):
    type_id = None

    def __init__(self, args):
        self._args = args

    @property
    def url_data(self):
        return json.dumps({COMMAND_KEY: self.type_id,
                           DATA_KEY: self.get_elements()},
                          separators=(',', ':'))

    @property
    def url_title(self):
        title_str = unicode(self.get_elements())
        title_str = title_str.replace('[', '').replace(']', '')
        return title_str

    def get_elements(self):
        return None

    def execute(self):
        return None


class SelectElementsCommand(GenericProtocolCommand):
    type_id = ProtocolCommandTypes.SELECT

    def get_elements(self):
        return [arg.IntegerValue for arg in self._args
                if isinstance(arg, DB.ElementId)]

    def execute(self):
        el_list = List[DB.ElementId]()
        for arg in self._args:
            if type(arg) == int:
                el_list.Add(DB.ElementId(arg))

        if not HOST_APP.doc:
            logger.debug('Active document does not exist in Revit. '
                         'Can not get doc and uidoc.')
        else:
            HOST_APP.uidoc.Selection.SetElementIds(el_list)

            for ei_id in el_list:
                try:
                    el = HOST_APP.doc.GetElement(ei_id)
                    if isinstance(el, DB.View):
                        HOST_APP.uidoc.ActiveView = el
                    else:
                        owner_view = HOST_APP.doc.GetElement(el.OwnerViewId)
                        if owner_view:
                            HOST_APP.uidoc.ActiveView = owner_view
                except Exception as err:
                    print(err)


def _get_command_from_arg(cmd_args):
    # Work-in-progress
    # only returning the select command at the moment
    return SelectElementsCommand(cmd_args)


def _get_command_from_data(cmd_data):
    # Work-in-progress
    # only processing the select command at the moment
    cmd_dict = json.loads(cmd_data)
    if cmd_dict[COMMAND_KEY] == ProtocolCommandTypes.SELECT:
        return SelectElementsCommand(cmd_dict[DATA_KEY])


def _make_protocol_url(url_data, url_title):
    return DEFAULT_LINK.format(PROTOCOL_NAME,
                               url_data.replace('\"', '\''), url_title)


def make_url(args):
    """
    Receives the input data, determines the appropriate command and returns
    the url loaded with json data.

    Args:
        args:

    Returns:
        str: Data string in json format

    Examples:
        Data contains a list of element ids to be selected.
        >>> element_id = DB.ElementId(1235)
        >>> make_url(element_id)
        >>> "revit://{'command':'select','data':[1235]}"
    """
    # send the arguments and receive the handling command for this input.
    cmd = _get_command_from_arg(args)
    # command contains the data string and a
    # title for the html link block or other uses.
    return _make_protocol_url(cmd.url_data, cmd.url_title)


def process_url(url):
    """
    Receives the data string in json format and processes the input.
    the json data needs to define 'command' and 'data' keys, providing
    the command name and the data to be sent to the command.

    Notice that the data string uses ' characters to contain the keys and
     not the " required by json. This is due to the fact that " characters
     are also used in html to contain values and this causes issues.

    The functions here, replace the " with ' when making the url and,
    ' with " when processing the urls.

    Args:
        url (str): Data string in json format

    Returns:
        None

    Examples:
        Data contains a list of element ids to be selected.
        >>> url_ = "revit://{'command':'select', 'data':[123456]}"
        >>> process_url(url)
    """
    # cleanup protocol name, / and change single quotes back to double quotes
    url_data = url.replace(PROTOCOL_NAME,
                           '').replace('/',
                                       '').replace('\'',
                                                   '\"')
    # send the string data to be processed and the command object, then execute
    cmd = _get_command_from_data(url_data)
    return cmd.execute()
