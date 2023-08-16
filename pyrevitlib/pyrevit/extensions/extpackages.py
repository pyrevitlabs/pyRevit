"""Base module to handle processing extensions as packages."""
import os
import os.path as op
import codecs
import json
from collections import defaultdict

from pyrevit import PyRevitException, HOST_APP
from pyrevit import labs
from pyrevit.compat import safe_strtype
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import git, fully_remove_dir
from pyrevit.userconfig import user_config

from pyrevit import extensions as exts


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


class PyRevitPluginAlreadyInstalledException(PyRevitException):
    """Exception raised when extension is already installed."""
    def __init__(self, extpkg):
        super(PyRevitPluginAlreadyInstalledException, self).__init__()
        self.extpkg = extpkg
        PyRevitException(self)


class PyRevitPluginNoInstallLinkException(PyRevitException):
    """Exception raised when extension does not have an install link."""
    pass


class PyRevitPluginRemoveException(PyRevitException):
    """Exception raised when removing an extension."""
    pass


PLUGIN_EXT_DEF_MANIFEST_NAME = 'extensions'
PLUGIN_EXT_DEF_FILE = PLUGIN_EXT_DEF_MANIFEST_NAME + exts.JSON_FILE_FORMAT

EXTENSION_POSTFIXES = [x.POSTFIX for x in exts.ExtensionTypes.get_ext_types()]


class DependencyGraph:
    """Extension packages dependency graph."""
    def __init__(self, extpkg_list):
        self.dep_dict = defaultdict(list)
        self.extpkgs = extpkg_list
        for extpkg in extpkg_list:
            if extpkg.dependencies:
                for dep_pkg_name in extpkg.dependencies:
                    self.dep_dict[dep_pkg_name].append(extpkg)

    def has_installed_dependents(self, extpkg_name):
        if extpkg_name in self.dep_dict:
            for dep_pkg in self.dep_dict[extpkg_name]:
                if dep_pkg.is_installed:
                    return True
        else:
            return False


class ExtensionPackage:
    """Extension package class.

    This class contains the extension information and also manages installation,
    user configuration, and removal of the extension.
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
        """Initialized the extension class based on provide information.

        Required info (Dictionary keys):
            type, name, description, url

        Optional info:
            website, image, author, author-url, authusers

        Args:
            info_dict (dict): A dictionary containing the required information
                              for initializing the extension.
            def_file_path (str): The file path of the extension definition file
        """
        self.type = exts.ExtensionTypes.UI_EXTENSION
        self.builtin = False
        self.default_enabled = True
        self.name = None
        self.description = None
        self.url = None
        self.def_file_path = set()
        self.authusers = set()
        self.authgroups = set()
        self.rocket_mode_compatible = False
        self.website = None
        self.image = None
        self.author = None
        self.author_profile = None
        self.dependencies = set()

        self.update_info(info_dict, def_file_path=def_file_path)

    def update_info(self, info_dict, def_file_path=None):
        ext_def_type = info_dict.get('type', None)
        for ext_type in exts.ExtensionTypes.get_ext_types():
            if ext_def_type == ext_type.ID:
                self.type = ext_type

        self.builtin = \
            safe_strtype(info_dict.get('builtin',
                                       self.builtin)).lower() == 'true'

        self.default_enabled = safe_strtype(
            info_dict.get('default_enabled', self.default_enabled)
            ).lower() == 'true'

        self.name = info_dict.get('name', self.name)
        self.description = info_dict.get('description', self.description)
        self.url = info_dict.get('url', self.url)

        if def_file_path:
            self.def_file_path.add(def_file_path)

        # update list of authorized users
        authusers = info_dict.get('authusers', [])
        if authusers:
            self.authusers.update(authusers)

        # update list of authorized user groups
        authgroups = info_dict.get('authgroups', [])
        if authgroups:
            self.authgroups.update(authgroups)

        # rocket mode compatibility
        self.rocket_mode_compatible = \
            safe_strtype(
                info_dict.get('rocket_mode_compatible',
                              self.rocket_mode_compatible)
                ).lower() == 'true'

        # extended attributes
        self.website = info_dict.get(
            'website',
            self.url.replace('.git', '') if self.url else self.website
            )
        self.image = info_dict.get('image', self.image)
        self.author = info_dict.get('author', self.author)

        self.author_profile = info_dict.get('author_profile',
                                            self.author_profile)
        # update list dependencies
        depends = info_dict.get('dependencies', [])
        if depends:
            self.dependencies.update(depends)

    def is_valid(self):
        return self.name is not None and self.url is not None

    def __repr__(self):
        return '<ExtensionPackage object. name:\'{}\' url:\'{}\' auth:{}>'\
            .format(self.name, self.url, self.authusers)

    @property
    def ext_dirname(self):
        """Installation directory name to use.

        Returns:
            (str): The name that should be used for the installation directory
                (based on the extension type).
        """
        return self.name + self.type.POSTFIX

    @property
    def is_installed(self):
        """Installation directory.

        Returns:
            (str): Installed directory path or empty string if not installed.
        """
        for ext_dir in user_config.get_ext_root_dirs():
            if op.exists(ext_dir):
                for sub_dir in os.listdir(ext_dir):
                    if op.isdir(op.join(ext_dir, sub_dir))\
                            and sub_dir == self.ext_dirname:
                        return op.join(ext_dir, sub_dir)
            else:
                mlogger.error('custom Extension path does not exist: %s',
                              ext_dir)

        return ''

    @property
    def installed_dir(self):
        """Installation directory.

        Returns:
            (str): Installed directory path or empty string if not installed.
        """
        return self.is_installed

    @property
    def is_removable(self):
        """Whether the extension is safe to remove.

        Checks whether it is safe to remove this extension by confirming if
        a git url is provided for this extension for later re-install.

        Returns:
            (bool): True if removable, False if not
        """
        return True if self.url else False

    @property
    def version(self):
        """Extension version.

        Returns:
            (str): Last commit hash of the extension git repo.
        """
        try:
            if self.is_installed:
                extpkg_repo = git.get_repo(self.installed_dir)
                return extpkg_repo.last_commit_hash
        except Exception:
            return None

    @property
    def config(self):
        """Returns a valid config manager for this extension.

        All config parameters will be saved in user config file.

        Returns:
            (pyrevit.coreutils.configparser.PyRevitConfigSectionParser):
                Config section handler
        """
        try:
            return user_config.get_section(self.ext_dirname)
        except Exception:
            cfg_section = user_config.add_section(self.ext_dirname)
            self.config.disabled = not self.default_enabled
            self.config.private_repo = self.builtin
            self.config.username = self.config.password = ''
            user_config.save_changes()
            return cfg_section

    @property
    def is_enabled(self):
        """Checks the default and user configured load state of the extension.

        Returns:
            (bool): True if package should be loaded
        """
        return not self.config.disabled

    @property
    def user_has_access(self):
        """Checks whether current user has access to this extension.

        Returns:
            (bool): True is current user has access
        """
        if self.authusers:
            return HOST_APP.username in self.authusers
        elif self.authgroups:
            for authgroup in self.authgroups:
                if labs.Common.Security.UserAuth.\
                        UserIsInSecurityGroup(authgroup):
                    return True
        else:
            return True

    def remove_pkg_config(self):
        """Removes the installed extension configuration."""
        user_config.remove_section(self.ext_dirname)
        user_config.save_changes()

    def disable_package(self):
        """Disables package in pyRevit configuration.

        It won't be loaded in the next session.
        """
        self.config.disabled = True
        user_config.save_changes()

    def toggle_package(self):
        """Disables/Enables package in pyRevit configuration.

        A disabled package won't be loaded in the next session.
        """
        self.config.disabled = not self.config.disabled
        user_config.save_changes()


def _update_extpkgs(ext_def_file, loaded_pkgs):
    with codecs.open(ext_def_file, 'r', 'utf-8') as extpkg_def_file:
        try:
            extpkg_dict = json.load(extpkg_def_file)
            defined_exts_pkgs = [extpkg_dict]
            if PLUGIN_EXT_DEF_MANIFEST_NAME in extpkg_dict.keys():
                defined_exts_pkgs = \
                    extpkg_dict[PLUGIN_EXT_DEF_MANIFEST_NAME]
        except Exception as def_file_err:
            print('Can not parse plugin ext definition file: {} '
                  '| {}'.format(ext_def_file, def_file_err))
            return

    for extpkg_def in defined_exts_pkgs:
        extpkg = ExtensionPackage(extpkg_def, ext_def_file)
        matched_pkg = None
        for loaded_pkg in loaded_pkgs:
            if loaded_pkg.name == extpkg.name:
                matched_pkg = loaded_pkg
                break
        if matched_pkg:
            matched_pkg.update_info(extpkg_def)
        elif extpkg.is_valid():
            loaded_pkgs.append(extpkg)


def _install_extpkg(extpkg, install_dir, install_dependencies=True):
    is_installed_path = extpkg.is_installed
    if is_installed_path:
        raise PyRevitPluginAlreadyInstalledException(extpkg)

    # if package is installable
    if extpkg.url:
        clone_path = op.join(install_dir, extpkg.ext_dirname)
        mlogger.info('Installing %s to %s', extpkg.name, clone_path)

        if extpkg.config.username and extpkg.config.password:
            git.git_clone(extpkg.url, clone_path,
                          username=extpkg.config.username,
                          password=extpkg.config.password)
        else:
            git.git_clone(extpkg.url, clone_path)
        mlogger.info('Extension successfully installed :thumbs_up:')
    else:
        raise PyRevitPluginNoInstallLinkException()

    if install_dependencies:
        if extpkg.dependencies:
            mlogger.info('Installing dependencies for %s', extpkg.name)
            for dep_pkg_name in extpkg.dependencies:
                dep_pkg = get_ext_package_by_name(dep_pkg_name)
                if dep_pkg:
                    _install_extpkg(dep_pkg,
                                     install_dir,
                                     install_dependencies=True)


def _remove_extpkg(extpkg, remove_dependencies=True):
    if extpkg.is_removable:
        dir_to_remove = extpkg.is_installed
        if dir_to_remove:
            fully_remove_dir(dir_to_remove)
            extpkg.remove_pkg_config()
            mlogger.info('Successfully removed extension from: %s',
                         dir_to_remove)
        else:
            raise PyRevitPluginRemoveException('Can not find installed path.')
    else:
        raise PyRevitPluginRemoveException('Extension does not have url '
                                           'and can not be installed later.')

    if remove_dependencies:
        dg = get_dependency_graph()
        mlogger.info('Removing dependencies for %s', extpkg.name)
        for dep_pkg_name in extpkg.dependencies:
            dep_pkg = get_ext_package_by_name(dep_pkg_name)
            if dep_pkg and not dg.has_installed_dependents(dep_pkg_name):
                _remove_extpkg(dep_pkg, remove_dependencies=True)


def _find_internal_extpkgs(ext_dir):
    internal_extpkg_def_files = []
    mlogger.debug('Looking for internal package defs under %s', ext_dir)
    for subfolder in os.listdir(ext_dir):
        if any([subfolder.endswith(x) for x in EXTENSION_POSTFIXES]):
            mlogger.debug('Found extension folder %s', subfolder)
            int_extpkg_deffile = \
                op.join(ext_dir, subfolder, exts.EXT_MANIFEST_FILE)
            mlogger.debug('Looking for %s', int_extpkg_deffile)
            if op.exists(int_extpkg_deffile):
                mlogger.debug('Found %s', int_extpkg_deffile)
                internal_extpkg_def_files.append(int_extpkg_deffile)
    return internal_extpkg_def_files


def get_ext_packages(authorized_only=True):
    """Returns the registered plugin extensions packages.

    Reads the list of registered plug-in extensions and returns a list of
    ExtensionPackage classes which contain information on the plug-in extension.

    Args:
        authorized_only (bool): Only return authorized extensions

    Returns:
        (list[ExtensionPackage]): list of registered plugin extensions
    """
    extpkgs = []
    for ext_dir in user_config.get_ext_root_dirs():
        # make a list of all availabe extension definition sources
        # default is under the extensions directory that ships with pyrevit
        extpkg_def_files = {op.join(ext_dir, PLUGIN_EXT_DEF_FILE)}
        # add other sources added by the user (using the cli)
        extpkg_def_files.update(user_config.get_ext_sources())
        for extpkg_def_file in extpkg_def_files:
            mlogger.debug('Looking for %s', extpkg_def_file)
            # check for external ext def file
            if op.exists(extpkg_def_file):
                mlogger.debug('Found %s', extpkg_def_file)
                _update_extpkgs(extpkg_def_file, extpkgs)
            # check internals now
            internal_extpkg_defs = _find_internal_extpkgs(ext_dir)
            for int_def_file in internal_extpkg_defs:
                _update_extpkgs(int_def_file, extpkgs)

    if authorized_only:
        return [x for x in extpkgs if x.user_has_access]

    return extpkgs


def get_ext_package_by_name(extpkg_name):
    for extpkg in get_ext_packages(authorized_only=False):
        if extpkg.name == extpkg_name:
            return extpkg
    return None


def get_dependency_graph():
    return DependencyGraph(get_ext_packages(authorized_only=False))


def install(extpkg, install_dir, install_dependencies=True):
    """Install the extension in the given parent directory.

    This method uses .installed_dir property of extension object 
    as installation directory name for this extension.
    This method also handles installation of extension dependencies.

    Args:
        extpkg (ExtensionPackage): Extension package to be installed
        install_dir (str): Parent directory to install extension in.
        install_dependencies (bool): Install the dependencies as well

    Raises:
        PyRevitException: on install error with error message
    """
    try:
        _install_extpkg(extpkg, install_dir, install_dependencies)
    except PyRevitPluginAlreadyInstalledException as already_installed_err:
        mlogger.warning('%s extension is already installed under %s',
                        already_installed_err.extpkg.name,
                        already_installed_err.extpkg.is_installed)
    except PyRevitPluginNoInstallLinkException:
        mlogger.error('Extension does not have an install link '
                      'and can not be installed.')


def remove(extpkg, remove_dependencies=True):
    """Removes the extension.

    Removes the extension from its installed directory
    and clears its configuration.

    Args:
        extpkg (ExtensionPackage): Extension package to be removed
        remove_dependencies (bool): Remove the dependencies as well

    Raises:
        PyRevitException: on remove error with error message
    """
    try:
        _remove_extpkg(extpkg, remove_dependencies)
    except PyRevitPluginRemoveException as remove_err:
        mlogger.error('Error removing extension: %s | %s',
                      extpkg.name, remove_err)
