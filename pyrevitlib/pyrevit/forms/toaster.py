"""Base module for pushing toast messages on Win 10.

This module is a wrapper for a cli utility that provides toast message
functionality. See `https://github.com/go-toast/toast`
"""

import os.path as op
import subprocess

from pyrevit import ROOT_BIN_DIR
from pyrevit.coreutils.logger import get_logger


#pylint: disable=W0703,C0302
mlogger = get_logger(__name__)  #pylint: disable=C0103


def get_toaster():
    """Return full file path of the toast binary utility."""
    return op.join(op.dirname(__file__), 'pyrevit-toast.exe')


def send_toast(message,
               title=None, appid=None, icon=None, click=None, actions=None):
    """Send toast notificaton.

    Args:
        message (str): notification message
        title (str): notification title
        appid (str): application unique id (see `--app-id` cli option)
        icon (str): notification icon (see `--icon` cli option)
        click (str): click action (see `--activation-arg` cli option)
        actions (dict[str:str]):
            list of actions (see `--action` and `--action-arg` cli options)
    """
    # set defaults
    if not title:
        title = 'pyRevit'
    if not appid:
        appid = title
    if not icon:
        icon = op.join(ROOT_BIN_DIR, 'pyRevit.ico')
    if not actions:
        actions = {}

    # build the toast
    toast_args = r'"{}"'.format(get_toaster())
    toast_args += r' --app-id "{}"'.format(appid)
    toast_args += r' --title "{}"'.format(title)
    toast_args += r' --message "{}"'.format(message)
    toast_args += r' --icon "{}"'.format(icon)
    toast_args += r' --audio "default"'
    # toast_args += r' --duration "long"'
    if click:
        toast_args += r' --activation-arg "{}"'.format(click)
    for action, args in actions.items():
        toast_args += r' --action "{}" --action-arg "{}"'.format(action, args)

    # send the toast now
    mlogger.debug('toasting: %s', toast_args)
    subprocess.Popen(toast_args, shell=True)
