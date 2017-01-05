# perform upgrades between versions here, e.g. adding a new config parameter
from pyrevit.userconfig import user_config


def _filelogging_config_upgrade():
    try:
        assert user_config.core.filelogging
    except:
        user_config.core.filelogging = False
        user_config.save_changes()


def upgrade_existing_pyrevit():
    # _filelogging_config_upgrade()
    pass
