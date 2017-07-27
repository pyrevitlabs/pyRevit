"""Prints calculated hash values for each extension."""

__title__ = 'Get Extension\nHash Values'

from scriptutils import logger
from pyrevit.extensions.extensionmgr import get_installed_ui_extensions

logger.set_quiet_mode()

for ui_ext in get_installed_ui_extensions():
    print('{}\t\tExtension: {}'.format(ui_ext.dir_hash_value, ui_ext.name))
