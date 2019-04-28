"""Base module for pushing toast messages on Win 10."""

import os.path as op
import subprocess

from pyrevit import BIN_DIR
from pyrevit.coreutils.logger import get_logger
from pyrevit import coreutils


#pylint: disable=W0703,C0302
mlogger = get_logger(__name__)  #pylint: disable=C0103


def get_toaster():
    return op.join(BIN_DIR, 'toast64.exe')


def send_toast(message,
               title=None, appid=None, icon=None, click=None, actions=None):
    # set defaults
    if not title:
        title = 'pyRevit'
    if not appid:
        appid = title
    if not icon:
        icon = op.join(BIN_DIR, 'pyRevit.ico')
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