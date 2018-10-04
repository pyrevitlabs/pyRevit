"""Base module to handle processing extensions as packages."""
import os
import os.path as op
import codecs
import json
from collections import defaultdict

from pyrevit import PyRevitException, HOST_APP
from pyrevit.compat import safe_strtype
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import git, fully_remove_dir
from pyrevit.userconfig import user_config

from pyrevit.extensions import ExtensionTypes


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


class PyRevitPluginAlreadyInstalledException(PyRevitException):
    def __init__(self, ext_pkg):
        super(PyRevitPluginAlreadyInstalledException, self).__init__()
        self.ext_pkg = ext_pkg
        PyRevitException(self)


class PyRevitPluginNoInstallLinkException(PyRevitException):
    pass


class PyRevitPluginRemoveException(PyRevitException):
    pass


PLUGIN_EXT_DEF_FILE = 'extensions.json'


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
        Initialized the extension class based on provide information

        Required info (Dictionary keys):
            type, name, description, url

        Optional info:
            website, image, author, author-url, authusers

        Args:
            info_dict (dict): A dictionary containing the required information
                              for initializing the extension.
            def_file_path (str): The file path of the extension definition file
        """
        self.type = ExtensionTypes.UI_EXTENSION
        self.builtin = False
        self.default_enabled = True
        self.name = None
        self.description = None
        self.url = None
        self.def_file_path = set()
        self.authusers = set()
        self.rocket_mode_compatible = False
        self.website = None
        self.image = None
        self.author = None
        self.author_profile = None
        self.dependencies = set()

        self.update_info(info_dict, def_file_path=def_file_path)

    def update_info(self, info_dict, def_file_path=None):
        ext_type = info_dict.get('type', None)
        if ext_type == ExtensionTypes.LIB_EXTENSION.ID:
            self.type = ExtensionTypes.LIB_EXTENSION

        self.builtin = \
            safe_strtype(info_dict.get('builtin',
                                       self.builtin)).lower() == 'true'

        # show deprecation warning on author-url
        if 'enable' in info_dict:
            self.default_enabled = safe_strtype(
                info_dict.get('enable', self.default_enabled)
                ).lower() == 'true'
            mlogger.deprecate(
                "Naming of \"enable\" property in extension.json files "
                "has changed. Please revise your extension.json files to "
                "use \"default_enabled\" (with underscore) instead.")
        else:
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

        # show deprecation warning on author-url
        if 'author-url' in info_dict:
            self.author_profile = info_dict.get('author-url',
                                                self.author_profile)
            mlogger.deprecate(
                "Naming of \"author-url\" property in extension.json files "
                "has changed. Please revise your extension.json files to "
                "use \"author_profile\" (with underscore) instead.")
        else:
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
                mlogger.error('custom Extension path does not exist: %s',
                              ext_dir)

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
        except Exception:
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


def _update_ext_pkgs(ext_def_file, loaded_pkgs):
    with codecs.open(ext_def_file, 'r', 'utf-8') as ext_pkg_def_file:
        try:
            defined_exts_pkg = json.load(ext_pkg_def_file)['extensions']
        except Exception as def_file_err:
            print('Can not parse plugin ext definition file: {} '
                  '| {}'.format(ext_def_file, def_file_err))
            return

    for ext_pkg_dict in defined_exts_pkg:
        ext_pkg = ExtensionPackage(ext_pkg_dict, ext_def_file)
        matched_pkg = None
        for loaded_pkg in loaded_pkgs:
            if loaded_pkg.name == ext_pkg.name:
                matched_pkg = loaded_pkg
                break
        if matched_pkg:
            matched_pkg.update_info(ext_pkg_dict)
        elif ext_pkg.is_valid():
            loaded_pkgs.append(ext_pkg)


def _install_ext_pkg(ext_pkg, install_dir, install_dependencies=True):
    is_installed_path = ext_pkg.is_installed
    if is_installed_path:
        raise PyRevitPluginAlreadyInstalledException(ext_pkg)

    # if package is installable
    if ext_pkg.url:
        clone_path = op.join(install_dir, ext_pkg.ext_dirname)
        mlogger.info('Installing %s to %s', ext_pkg.name, clone_path)

        if ext_pkg.config.username and ext_pkg.config.password:
            git.git_clone(ext_pkg.url, clone_path,
                          username=ext_pkg.config.username,
                          password=ext_pkg.config.password)
        else:
            git.git_clone(ext_pkg.url, clone_path)
        mlogger.info('Extension successfully installed :thumbs_up:')
    else:
        raise PyRevitPluginNoInstallLinkException()

    if install_dependencies:
        if ext_pkg.dependencies:
            mlogger.info('Installing dependencies for %s', ext_pkg.name)
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
            fully_remove_dir(dir_to_remove)
            ext_pkg.remove_pkg_config()
            mlogger.info('Successfully removed extension from: %s',
                         dir_to_remove)
        else:
            raise PyRevitPluginRemoveException('Can not find installed path.')
    else:
        raise PyRevitPluginRemoveException('Extension does not have url '
                                           'and can not be installed later.')

    if remove_dependencies:
        dg = get_dependency_graph()
        mlogger.info('Removing dependencies for %s', ext_pkg.name)
        for dep_pkg_name in ext_pkg.dependencies:
            dep_pkg = get_ext_package_by_name(dep_pkg_name)
            if dep_pkg and not dg.has_installed_dependents(dep_pkg_name):
                _remove_ext_pkg(dep_pkg, remove_dependencies=True)


def get_ext_packages(authorized_only=True):
    """
    Reads the list of registered plug-in extensions and returns a list of
    ExtensionPackage classes which contain information on the
    plug-in extension.

    Returns:
        list: list of registered plugin extensions (ExtensionPackage)
    """
    ext_pkgs = []
    for ext_dir in user_config.get_ext_root_dirs():
        ext_pkg_deffile = op.join(ext_dir, PLUGIN_EXT_DEF_FILE)
        if op.exists(ext_pkg_deffile):
            _update_ext_pkgs(ext_pkg_deffile, ext_pkgs)

    if authorized_only:
        return [x for x in ext_pkgs if x.user_has_access]

    return ext_pkgs


def get_ext_package_by_name(ext_pkg_name):
    for ext_pkg in get_ext_packages(authorized_only=False):
        if ext_pkg.name == ext_pkg_name:
            return ext_pkg
    return None


def get_dependency_graph():
    return DependencyGraph(get_ext_packages(authorized_only=False))


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
        mlogger.warning('%s extension is already installed under %s',
                        already_installed_err.ext_pkg.name,
                        already_installed_err.ext_pkg.is_installed)
    except PyRevitPluginNoInstallLinkException:
        mlogger.error('Extension does not have an install link '
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
        mlogger.error('Error removing extension: %s | %s',
                      ext_pkg.name, remove_err)
