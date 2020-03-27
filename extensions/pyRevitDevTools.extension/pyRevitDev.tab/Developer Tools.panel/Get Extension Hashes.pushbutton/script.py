"""Prints calculated hash values for each extension."""

__title__ = 'Get Extension\nHash Values'
__highlight__= 'updated'
__context__ = 'zero-doc'
# __beta__ = True

from pyrevit import script
from pyrevit.extensions import extensionmgr


logger = script.get_logger()
logger.set_quiet_mode()


for ui_ext in extensionmgr.get_installed_ui_extensions():
    print('{}\t\tExtension: {}'.format(ui_ext.dir_hash_value, ui_ext.name))


logger.reset_level()
