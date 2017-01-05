import os.path as op
import json

from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config

from pyrevit.plugins import PLUGIN_EXT_DEF_FILE


logger = get_logger(__name__)


class ExtensionPackage:
    def __init__(self, info_dict):
        try:
            self.type = info_dict['type']
            self.name = info_dict['name']
            self.description = info_dict['description']
            self.url = info_dict['url']
        except KeyError as ext_info_err:
            raise PyRevitException('Required plugin ext info not available. | {}'.format(ext_info_err))

        try:
            self.website = info_dict['website']
            self.image = info_dict['image']
        except Exception as ext_info_err:
            logger.debug('Missing extended plugin ext info. | {}'.format(ext_info_err))

    def keys(self):
        return self.__dict__.keys()

    def __getitem__(self, item):
        return self.__dict__[item]

    @property
    def is_installed(self):
        return False


def get_ext_packages():
    """
    Reads the list of registered plug-in extensions and returns a list of ExtensionPackage classes which contain
    information on the plug-in extension.

    Returns:
        list: list of registered plugin extensions (ExtensionPackage)
    """

    ext_dirs = user_config.get_ext_root_dirs()
    ext_pkgs = []

    for ext_dir in ext_dirs:
        ext_pkg_def_file_path = op.join(ext_dir, PLUGIN_EXT_DEF_FILE)
        if op.exists(ext_pkg_def_file_path):
            with open(ext_pkg_def_file_path, 'r') as ext_pkg_def_file:
                try:
                    defined_exts_pkg = json.load(ext_pkg_def_file)['extensions']
                    for ext_pkg_dict in defined_exts_pkg:
                        try:
                            ext_pkgs.append(ExtensionPackage(ext_pkg_dict))
                        except Exception as ext_pkg_err:
                            logger.debug('Error creating ExtensionPackage class. | {}'.format(ext_pkg_err))

                except Exception as def_file_err:
                    logger.debug('Can not parse plugin ext definition file: {} | {}'.format(ext_pkg_def_file_path,
                                                                                            def_file_err))

    return ext_pkgs
