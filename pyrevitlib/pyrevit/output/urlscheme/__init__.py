import json

from pyrevit import revit, DB, UI
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger

from pyrevit.output.urlscheme import baseunivcmd
from pyrevit.output.urlscheme import schemecmds


logger = get_logger(__name__)


def _get_available_schemecmds():
    return coreutils.get_all_subclasses([baseunivcmd.GenericUniversalCommand])


def _get_command_from_arg(cmd_args):
    # Work-in-progress
    # only returning the select command at the moment
    return schemecmds.SelectElementsCommand(cmd_args)


def _get_command_from_url_payload(url_payload):
    # Work-in-progress
    # only processing the select command at the moment
    payload_dict = json.loads(url_payload)

    command_classes = _get_available_schemecmds()

    if command_classes:
        for cmd in command_classes:
            if payload_dict[baseunivcmd.COMMAND_KEY] == cmd.type_id:
                return cmd(payload_dict[baseunivcmd.DATA_KEY])


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
    return cmd.make_command_url()


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
    # cleanup scheme name, / and change single quotes back to double quotes
    url_data = url.replace(baseunivcmd.SCHEME_PREFIX, '') \
                  .replace('/', '') \
                  .replace('\'', '\"')
    # send the string data to be processed and the command object, then execute
    cmd = _get_command_from_url_payload(url_data)
    return cmd.execute()


def handle_scheme_url(url):
    """
    This is a function assgined to the ScriptOutput.UrlHandler which
     is a delegate. Everytime WebBrowser is asked to handle a link with
     a scheme other than http, it'll call this function.
    System.Windows.Forms.WebBrowser returns a string with misc stuff
     before the actual link, when it can't recognize the scheme.
    This function cleans up the link for the pyRevit scheme handler.

    Args:
        url (str): the url coming from Forms.WebBrowser
    """
    try:
        if baseunivcmd.SCHEME_PREFIX in url:
            cleaned_url = url.split(baseunivcmd.SCHEME_PREFIX)[1]
            # get rid of the slash at the end
            if cleaned_url.endswith('/'):
                cleaned_url = cleaned_url.replace('/', '')

            # process cleaned data
            process_url(cleaned_url)
    except Exception as exec_err:
        logger.error('Error handling link | {}'.format(exec_err))
