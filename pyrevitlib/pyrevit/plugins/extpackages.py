import os
import os.path as op
import json
import shutil

from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import git
from pyrevit.userconfig import user_config

from pyrevit.extensions import ExtensionTypes
from pyrevit.plugins import PLUGIN_EXT_DEF_FILE


logger = get_logger(__name__)


class ExtensionPackage:
    def __init__(self, info_dict, def_file_path):
        # Setting required attributes
        try:
            ext_type = info_dict['type']
            if ext_type == ExtensionTypes.UI_EXTENSION.ID:
                self.type = ExtensionTypes.UI_EXTENSION
            elif ext_type == ExtensionTypes.LIB_EXTENSION.ID:
                self.type = ExtensionTypes.LIB_EXTENSION

            self.name = info_dict['name']
            self.description = info_dict['description']
            self.url = info_dict['url']

            self.installed_dir = None
            self.def_file_path = def_file_path
        except KeyError as ext_info_err:
            raise PyRevitException('Required plugin ext info not available. | {}'.format(ext_info_err))

        # Setting extended attributes
        try:
            self.website = info_dict['website']
            self.image = info_dict['image']
        except Exception as ext_info_err:
            self.website = self.image = None
            logger.debug('Missing extended plugin ext info. | {}'.format(ext_info_err))

    def __repr__(self):
        return '<ExtensionPackage object. name \'{}\' url \'{}\'>'.format(self.name, self.url)

    @property
    def ext_dirname(self):
        return self.name + self.type.POSTFIX

    @property
    def is_installed(self):
        for ext_dir in user_config.get_ext_root_dirs():
            for sub_dir in os.listdir(ext_dir):
                if op.isdir(op.join(ext_dir, sub_dir)) and sub_dir == self.ext_dirname:
                    return op.join(ext_dir, sub_dir)

        return ''

    @property
    def is_removable(self):
        return True if self.url else False

    def install(self, install_dir):
        is_installed_path = self.is_installed
        if is_installed_path:
            raise PyRevitException('Extension already installed under: {}'.format(is_installed_path))

        if self.url:
            clone_path = op.join(install_dir, self.ext_dirname)
            git.git_clone(self.url, clone_path)
            self.installed_dir = clone_path
        else:
            raise PyRevitException('Extension does not have url and can not be installed.')

    def remove(self):
        if self.is_removable:
            dir_to_remove = self.is_installed
            if dir_to_remove:
                shutil.rmtree(dir_to_remove)
                logger.debug('Successfully removed extension from: {}'.format(dir_to_remove))
            else:
                raise PyRevitException('Error removing extension. Can not find installed directory.')
        else:
            raise PyRevitException('Can not remove extension that does not have url and can not be installed later.')


class ExtensionPackageDefinitionFile:
    def __init__(self, file_path):
        self.file_path = file_path

    @property
    def defined_ext_packages(self):
        """
        Contains a list of extensions that are defined in this file (ExtensionPackage)

        Returns:
            list: List of ExtensionPackage objects that are defined in this file
        """

        ext_pkgs = []
        with open(self.file_path, 'r') as ext_pkg_def_file:
            try:
                defined_exts_pkg = json.load(ext_pkg_def_file)['extensions']
                for ext_pkg_dict in defined_exts_pkg:
                    try:
                        ext_pkgs.append(ExtensionPackage(ext_pkg_dict, self.file_path))
                    except Exception as ext_pkg_err:
                        logger.debug('Error creating ExtensionPackage class. | {}'.format(ext_pkg_err))

            except Exception as def_file_err:
                logger.debug('Can not parse plugin ext definition file: {} | {}'.format(self.file_path, def_file_err))

        return ext_pkgs


def get_ext_packages():
    """
    Reads the list of registered plug-in extensions and returns a list of ExtensionPackage classes which contain
    information on the plug-in extension.

    Returns:
        list: list of registered plugin extensions (ExtensionPackage)
    """

    ext_pkgs = []

    for ext_dir in user_config.get_ext_root_dirs():
        ext_pkg_def_file_path = op.join(ext_dir, PLUGIN_EXT_DEF_FILE)
        if op.exists(ext_pkg_def_file_path):
            ext_def_file = ExtensionPackageDefinitionFile(ext_pkg_def_file_path)
            ext_pkgs.extend(ext_def_file.defined_ext_packages)

    return ext_pkgs
