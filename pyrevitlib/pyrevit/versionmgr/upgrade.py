"""
perform upgrades between versions here,
e.g. adding a new config parameter

"""
#pylint: disable=W0611
from pyrevit.coreutils import appdata
from pyrevit.coreutils import find_loaded_asm, get_revit_instance_count


def upgrade_user_config(user_config):   #pylint: disable=W0613
    # upgrade value formats
    for section in user_config:
        for option in section:
            setattr(section, option, getattr(section, option))

    # fix legacy requiredhostbuild format
    req_build = user_config.core.get_option('requiredhostbuild',
                                            default_value="")
    if req_build == "0" or req_build == 0:
        user_config.core.requiredhostbuild = ""


def upgrade_existing_pyrevit():
    pass
