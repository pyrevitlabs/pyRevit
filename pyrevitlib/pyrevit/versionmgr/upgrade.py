"""Perform upgrades between version, e.g. adding a new config parameter."""
#pylint: disable=W0611
import os
import os.path as op

from pyrevit.coreutils import appdata


def upgrade_user_config(user_config):   #pylint: disable=W0613
    """Upgarde user configurations.

    Args:
        user_config (:obj:`pyrevit.userconfig.PyRevitConfig`): config object
    """
    # upgrade value formats
    for section in user_config:
        for option in section:
            setattr(section, option, getattr(section, option))


def remove_leftover_temp_files():
    """4.8.5 had a bug that would create temp files with extension ..bak.

    This cleans them up.
    """
    univ_path = op.dirname(appdata.get_universal_data_file("X", 'bak'))
    if op.exists(univ_path):
        for entry in os.listdir(univ_path):
            if op.isfile(entry) and entry.lower().endswith('..bak'):
                appdata.garbage_data_file(op.join(univ_path, entry))


def upgrade_existing_pyrevit():
    """Upgrade existing pyRevit deployment."""
    remove_leftover_temp_files()
