import os
import os.path as op
import json
from collections import defaultdict

from pyrevit import PyRevitException, HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import git, fully_remove_tree
from pyrevit.userconfig import user_config

from pyrevit.extensions import ExtensionTypes
from pyrevit.plugins import PLUGIN_EXT_DEF_FILE
from pyrevit.plugins import PyRevitPluginAlreadyInstalledException,\
                            PyRevitPluginNoInstallLinkException, \
                            PyRevitPluginRemoveException


logger = get_logger(__name__)


class DependencyGraph:
    def __init__(self, ext_pkg_list):
        self.dep_dict = defaultdict(list)
        self.ext_pkgs = ext_pkg_list
        for ext_pkg in ext_pkg_list:
            if ext_pkg.dependencies:
                for dep_pkg_name in ext_pkg.dependencies:
                    self.dep_dict[dep_pkg_name].append(ext_pkg)

    def has_installed_dependents(self, ext_pkg_name):
        if ext_pkg_name in self.dep_dict:
            for dep_pkg in self.dep_dict[ext_pkg_name]:
                if dep_pkg.is_installed:
                    return True
        else:
            return False


class ExtensionPackage:
    """
    Extension package class. This class contains the extension information and
    also manages installation, user configuration, and removal of the extension.
    See the ``__init__`` class documentation for the required and
    optional extension information.

    Attributes:
        type (extensions.ExtensionTypes): Extension type
        name (str): Extension name
        description (str): Extension description
        url (str): Url of online git repository
        website (str): Url of extension website
        image (str): Url of extension icon image (.png file)
        author (str): Name of extension author
        author_profile (str): Url of author profile
    """

    def __init__(self, info_dict, def_file_path=None):
        """
        Initialized the extension class based on provide information (info_dict)

        Required info (Dictionary keys):
            type, name, description , url

        Optional info:
            website, image, author, author-url

        Args:
            info_dict (dict): A dictionary containing the required information
                              for initializing the extension.
            def_file_path (str): The file path of the extension definition file
        """

        # Setting required attributes
        try:
            ext_type = info_dict['type']
            if ext_type == ExtensionTypes.UI_EXTENSION.ID:
                self.type = ExtensionTypes.UI_EXTENSION
            elif ext_type == ExtensionTypes.LIB_EXTENSION.ID:
                self.type = ExtensionTypes.LIB_EXTENSION

            self.builtin = info_dict['builtin'].lower() == 'true'
            self.enable_default = info_dict['enable'].lower() == 'true'

            self.name = info_dict['name']
            self.description = info_dict['description']
            self.url = info_dict['url']

            self.def_file_path = def_file_path
        except KeyError as ext_info_err:
            raise PyRevitException('Required plugin ext info not available. '
                                   '| {}'.format(ext_info_err))

        # Setup access
        if 'authusers' in info_dict:
            self.authusers = info_dict['authusers']
        else:
            self.authusers = None

        # Setting extended attributes
        try:
            self.website = info_dict['website']
            self.image = info_dict['image']
            self.author = info_dict['author']
            self.author_profile = info_dict['author-url']
            self.dependencies = info_dict['dependencies']
        except Exception as ext_info_err:
            self.website = self.url.replace('.git', '')
            self.image = None
            self.author = self.author_profile = None
            self.dependencies = []
            logger.debug('Missing extended plugin ext info. | {}'
                         .format(ext_info_err))

    def __repr__(self):
        return '<ExtensionPackage object. name \'{}\' url \'{}\'>'\
            .format(self.name, self.url)

    @property
    def ext_dirname(self):
        """
        Returns:
            str: The name that should be used for the installation directory
                 (based on the extension type)
        """
        return self.name + self.type.POSTFIX

    @property
    def is_installed(self):
        """
        Returns:
            bool: Checked whether this extension is installed or not.
        """
        for ext_dir in user_config.get_ext_root_dirs():
            if op.exists(ext_dir):
                for sub_dir in os.listdir(ext_dir):
                    if op.isdir(op.join(ext_dir, sub_dir))\
                            and sub_dir == self.ext_dirname:
                        return op.join(ext_dir, sub_dir)
            else:
                logger.error('custom Extension path does not exist: {}'
                             .format(ext_dir))

        return ''

    @property
    def installed_dir(self):
        """
        Returns:
            str: Installed directory path or empty string if not installed
        """
        return self.is_installed

    @property
    def is_removable(self):
        """
        Checks whether it is safe to remove this extension by confirming if
        a git url is provided for this extension for later re-install.

        Returns:
            bool: True if removable, False if not
        """
        return True if self.url else False

    @property
    def version(self):
        """
        Returns:
            str: Last commit hash of the extension git repo
        """
        try:
            if self.is_installed:
                ext_pkg_repo = git.get_repo(self.installed_dir)
                return ext_pkg_repo.last_commit_hash
        except:
            return None

    @property
    def config(self):
        """
        Returns a valid config manager for this extension.
        All config parameters will be saved in user config file.

        Returns:
            pyrevit.coreutils.configparser.PyRevitConfigSectionParser:
            Config section handler
        """

        try:
            return user_config.get_section(self.ext_dirname)
        except:
            cfg_section = user_config.add_section(self.ext_dirname)
            self.config.disabled = not self.enable_default
            self.config.private_repo = self.builtin
            self.config.username = self.config.password = ''
            user_config.save_changes()
            return cfg_section

    @property
    def is_enabled(self):
        """Checks the default and user configured load state of the extension.

        Returns:
            bool: True if package should be loaded
        """
        return not self.config.disabled

    @property
    def user_has_access(self):
        """Checks whether current user has access to this extension.

        Returns:
            bool: True is current user has access
        """
        if self.authusers:
            return HOST_APP.username in self.authusers
        else:
            return True

    def remove_pkg_config(self):
        """
        Removes the installed extension configuration.
        """

        user_config.remove_section(self.ext_dirname)
        user_config.save_changes()

    def disable_package(self):
        """
        Disables package in pyRevit configuration so it won't be loaded
        in the next session.
        """

        self.config.disabled = True
        user_config.save_changes()

    def toggle_package(self):
        """
        Disables/Enables package in pyRevit configuration so it won't be loaded
        in the next session.
        """

        self.config.disabled = not self.config.disabled
        user_config.save_changes()


class _ExtensionPackageDefinitionFile:
    def __init__(self, file_path):
        self.file_path = file_path

    @property
    def defined_ext_packages(self):
        """
        Contains a list of extensions that are defined in this file
        (ExtensionPackage)

        Returns:
            list: List of ExtensionPackage objects that are defined in this file
        """

        ext_pkgs = []
        with open(self.file_path, 'r') as ext_pkg_def_file:
            try:
                defined_exts_pkg = json.load(ext_pkg_def_file)['extensions']
                for ext_pkg_dict in defined_exts_pkg:
                    try:
                        ext_pkgs.append(ExtensionPackage(ext_pkg_dict,
                                                         self.file_path))
                    except Exception as ext_pkg_err:
                        logger.debug('Error creating ExtensionPackage class. '
                                     '| {}'.format(ext_pkg_err))

            except Exception as def_file_err:
                logger.debug('Can not parse plugin ext definition file: {} '
                             '| {}'.format(self.file_path, def_file_err))

        return ext_pkgs


def _install_ext_pkg(ext_pkg, install_dir, install_dependencies=True):
    is_installed_path = ext_pkg.is_installed
    if is_installed_path:
        raise PyRevitPluginAlreadyInstalledException(ext_pkg)

    # if package is installable
    if ext_pkg.url:
        clone_path = op.join(install_dir, ext_pkg.ext_dirname)
        logger.info('Installing {} to {}'.format(ext_pkg.name, clone_path))

        if ext_pkg.config.username and ext_pkg.config.password:
            git.git_clone(ext_pkg.url, clone_path,
                          username=ext_pkg.config.username,
                          password=ext_pkg.config.password)
        else:
            git.git_clone(ext_pkg.url, clone_path)
        logger.info('Extension successfully installed :thumbs_up:')
    else:
        raise PyRevitPluginNoInstallLinkException()

    if install_dependencies:
        if ext_pkg.dependencies:
            logger.info('Installing dependencies for {}'.format(ext_pkg.name))
            for dep_pkg_name in ext_pkg.dependencies:
                dep_pkg = get_ext_package_by_name(dep_pkg_name)
                if dep_pkg:
                    _install_ext_pkg(dep_pkg,
                                     install_dir,
                                     install_dependencies=True)


def _remove_ext_pkg(ext_pkg, remove_dependencies=True):
    if ext_pkg.is_removable:
        dir_to_remove = ext_pkg.is_installed
        if dir_to_remove:
            fully_remove_tree(dir_to_remove)
            ext_pkg.remove_pkg_config()
            logger.info('Successfully removed extension from: {}'
                        .format(dir_to_remove))
        else:
            raise PyRevitPluginRemoveException('Can not find installed path.')
    else:
        raise PyRevitPluginRemoveException('Extension does not have url '
                                           'and can not be installed later.')

    if remove_dependencies:
        dg = get_dependency_graph()
        logger.info('Removing dependencies for {}'.format(ext_pkg.name))
        for dep_pkg_name in ext_pkg.dependencies:
            dep_pkg = get_ext_package_by_name(dep_pkg_name)
            if dep_pkg and not dg.has_installed_dependents(dep_pkg_name):
                _remove_ext_pkg(dep_pkg, remove_dependencies=True)


def get_ext_packages(authorized_only=True):
    """
    Reads the list of registered plug-in extensions and returns a list of
    ExtensionPackage classes which contain information on the plug-in extension.

    Returns:
        list: list of registered plugin extensions (ExtensionPackage)
    """
    ext_pkgs = []
    for ext_dir in user_config.get_ext_root_dirs():
        ext_pkg_deffile = op.join(ext_dir, PLUGIN_EXT_DEF_FILE)
        if op.exists(ext_pkg_deffile):
            ext_def_file = _ExtensionPackageDefinitionFile(ext_pkg_deffile)
            if authorized_only:
                auth_pkgs = [x for x in ext_def_file.defined_ext_packages
                             if x.user_has_access]
            else:
                auth_pkgs = ext_def_file.defined_ext_packages

            ext_pkgs.extend(auth_pkgs)

    return ext_pkgs


def get_ext_package_by_name(ext_pkg_name):
    for ext_pkg in get_ext_packages(authorized_only=False):
        if ext_pkg.name == ext_pkg_name:
            return ext_pkg
    return None


def get_dependency_graph():
    return DependencyGraph(get_ext_packages(authorized_only=False))


def is_ext_package_enabled(ext_pkg_name, ext_pkg_type_postfix):
    """
    Checks whether an extension is enabled or has been disable by the user.

    Args:
        ext_pkg_name (str): Extension package name
        ext_pkg_type_postfix (str): Postfix of extension type
                                    (.lib or .extension)

    Returns:
        bool: True if enabled, False if not
    """
    try:
        ext_pkg = get_ext_package_by_name(ext_pkg_name)
        if ext_pkg:
            return ext_pkg.is_enabled and ext_pkg.user_has_access
        else:
            logger.debug('Extension package is not defined: {}.{}'
                         .format(ext_pkg_name, ext_pkg_type_postfix))
            # Lets be nice and load the package if it is not defined
            return True
    except Exception as ext_check_err:
        logger.error('Error checking state for extension: {} of type: {} | {}'
                     .format(ext_pkg_name, ext_pkg_type_postfix, ext_check_err))
        return True


def install(ext_pkg, install_dir, install_dependencies=True):
    """
    Installed the extension in the given parent directory. This method uses
    .installed_dir property of extension object as installation directory name
    for this extension. This method also handles installation of
    extension dependencies.

    Args:
        ext_pkg (ExtensionPackage): Extension package to be installed
        install_dir (str): Parent directory to install extension in.
        install_dependencies (bool): Install the dependencies as well

    Raises:
        PyRevitException: on install error with error message
    """
    try:
        _install_ext_pkg(ext_pkg, install_dir, install_dependencies)
    except PyRevitPluginAlreadyInstalledException as already_installed_err:
        logger.warning('{} extension is already installed under {}'
                       .format(already_installed_err.ext_pkg.name,
                               already_installed_err.ext_pkg.is_installed))
    except PyRevitPluginNoInstallLinkException:
        logger.error('Extension does not have an install link '
                     'and can not be installed.')


def remove(ext_pkg, remove_dependencies=True):
    """
    Removes the extension from its installed directory and
    clears its configuration.

    Raises:
        PyRevitException: on remove error with error message
    """
    try:
        _remove_ext_pkg(ext_pkg, remove_dependencies)
    except PyRevitPluginRemoveException as remove_err:
        logger.error('Error removing extension: {} | {}'
                     .format(ext_pkg.name, remove_err))
