"""Perform upgrades between version, e.g. adding a new config parameter"""
#pylint: disable=W0611

def upgrade_user_config(user_config):   #pylint: disable=W0613
    """Upgarde user configurations.

    Args:
        user_config (:obj:`pyrevit.userconfig.PyRevitConfig`): config object
        val (type): desc
    """
    # upgrade value formats
    for section in user_config:
        for option in section:
            setattr(section, option, getattr(section, option))


def upgrade_existing_pyrevit():
    """Upgrade existing pyRevit deployment."""
    pass
