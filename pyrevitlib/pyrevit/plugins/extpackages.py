import os
import os.path as op
import json

from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import git, fully_remove_tree
from pyrevit.userconfig import user_config

from pyrevit.extensions import ExtensionTypes
from pyrevit.plugins import PLUGIN_EXT_DEF_FILE


logger = get_logger(__name__)


class ExtensionPackage:
    """
    Extension package class. This class contains the extension information and also manages installation,
    user configuration, and removal of the extension. See the ``__init__`` class documentation for the required and
    optional extension information.

    Attributes:
        type (extensions.ExtensionTypes): Extension type
        name (str): Extension name
        description (str): Extension description
        url (str): Url of online git repository
        website (str): Url of extension website
        icon (str): Url of extension icon image (.png file)
        author (str): Name of extension author
        author_profile (str): Url of author profile
        ext_dirname (str): The name that should be used for the installation directory (based on the extension type)
        is_installed (bool): Checked whether this extension is installed or not.
        installed_dir (str): Installed directory path or empty string if not installed
        is_removable (bool): Checks whether it is safe to remove this extension
        version (str): Last commit hash of the extension git repo
        config (pyrevit.coreutils.configparser.PyRevitConfigSectionParser): See below
    """

    def __init__(self, info_dict, def_file_path=None):
        """
        Initialized the extension class based on provide information (info_dict).

        Required info (dictionary key name):
            type = info_dict['type']
            name = info_dict['name']
            description = info_dict['description']
            url = info_dict['url']

        Optional info:
            website = info_dict['website']
            icon = info_dict['image']
            author = info_dict['author']
            author_profile = info_dict['author-url']

        Args:
            info_dict (dict): A dictionary containing the required information for initializing the extension.
            def_file_path (str): The file path of the extension definition file
        """

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

            self.def_file_path = def_file_path
        except KeyError as ext_info_err:
            raise PyRevitException('Required plugin ext info not available. | {}'.format(ext_info_err))

        # Setting extended attributes
        try:
            self.website = info_dict['website']
            self.image = info_dict['image']
            self.author = info_dict['author']
            self.author_profile = info_dict['author-url']
        except Exception as ext_info_err:
            self.website = self.url.replace('.git','')
            self.image = None
            self.author = self.author_profile = None
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
    def installed_dir(self):
        return self.is_installed

    @property
    def is_removable(self):
        """
        Checks whether it is safe to remove this extension by confirming if a git url is provided
        for this extension for later re-install.

        Returns:
            bool: True if removable, False if not
        """
        return True if self.url else False

    @property
    def version(self):
        try:
            if self.is_installed:
                ext_pkg_repo = git.get_repo(self.installed_dir)
                return ext_pkg_repo.last_commit_hash
        except:
            return None

    @property
    def config(self):
        """
        Returns a valid config manager for this extension. All config parameters will be saved in user config file.

        Returns:
            pyrevit.coreutils.configparser.PyRevitConfigSectionParser: Config section handler
        """

        try:
            return user_config.get_section(self.ext_dirname)
        except:
            cfg_section = user_config.add_section(self.ext_dirname)
            self.config.disabled = False
            self.config.private_repo = False
            self.config.username = self.config.password = ''
            return cfg_section

    def remove_pkg_config(self):
        """
        Removes the installed extension configuration.
        """

        user_config.remove_section(self.ext_dirname)
        user_config.save_changes()

    def install(self, install_dir):
        """
        Installed the extension in the given parent directory. This method uses .installed_dir property of this
        extension object as installation directory name for this extension.

        Args:
            install_dir (str): Parent directory that the extension should be installed in.

        Raises:
            PyRevitException: on install error with error message
        """

        is_installed_path = self.is_installed
        if is_installed_path:
            raise PyRevitException('Extension already installed under: {}'.format(is_installed_path))

        if self.url:
            clone_path = op.join(install_dir, self.ext_dirname)

            if self.config.username and self.config.password:
                git.git_clone(self.url, clone_path, username=self.config.username, password=self.config.password)
            else:
                git.git_clone(self.url, clone_path)
        else:
            raise PyRevitException('Extension does not have url and can not be installed.')

    def remove(self):
        """
        Removes the extension from its installed directory and clears its configuration.

        Raises:
            PyRevitException: on remove error with error message
        """

        if self.is_removable:
            dir_to_remove = self.is_installed
            if dir_to_remove:
                fully_remove_tree(dir_to_remove)
                self.remove_pkg_config()
                logger.debug('Successfully removed extension from: {}'.format(dir_to_remove))
            else:
                raise PyRevitException('Error removing extension. Can not find installed directory.')
        else:
            raise PyRevitException('Can not remove extension that does not have url and can not be installed later.')


class _ExtensionPackageDefinitionFile:
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
            ext_def_file = _ExtensionPackageDefinitionFile(ext_pkg_def_file_path)
            ext_pkgs.extend(ext_def_file.defined_ext_packages)

    return ext_pkgs


def is_ext_package_enabled(ext_pkg_name, ext_pkg_type_postfix):
    """
    Checks whether an extension is enabled or has been disable by the user.

    Args:
        ext_pkg_name (str): Extension package name
        ext_pkg_type_postfix (str): Postfix of extension type (.lib or .extension)

    Returns:
        bool: True if enabled, False if not
    """
    try:
        pkg_config = user_config.get_section(ext_pkg_name + ext_pkg_type_postfix)
        return not pkg_config.disabled
    except:
        return True
