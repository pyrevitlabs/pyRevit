"""Base classes for pyRevit extension components."""
import os.path as op
import json
import codecs

from pyrevit import PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils import yaml
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts
from pyrevit.extensions.genericcomps import GenericComponent
from pyrevit.extensions.genericcomps import GenericUIContainer
from pyrevit.extensions.genericcomps import GenericUICommand
from pyrevit.versionmgr import get_pyrevit_version


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# Derived classes here correspond to similar elements in Revit ui.
# Under Revit UI:
# Packages contain Tabs, Tabs contain, Panels, Panels contain Stacks,
# Commands, or Command groups
# ------------------------------------------------------------------------------
class NoButton(GenericUICommand):
    type_id = exts.NOGUI_COMMAND_POSTFIX


class LinkButton(GenericUICommand):
    type_id = exts.LINK_BUTTON_POSTFIX

    def __init__(self):
        GenericUICommand.__init__(self)
        self.assembly = self.command_class = None

    def __init_from_dir__(self, cmd_dir):
        GenericUICommand.__init_from_dir__(self, cmd_dir)
        self.assembly = self.command_class = None
        try:
            # reading script file content to extract parameters
            script_content = \
                coreutils.ScriptFileParser(self.get_full_script_address())

            self.assembly = script_content.extract_param(
                exts.MDATA_LINK_BUTTON_ASSEMBLY)  # type: str

            self.command_class = \
                script_content.extract_param(
                    exts.MDATA_LINK_BUTTON_COMMAND_CLASS)  # type: str

        except PyRevitException as err:
            mlogger.error(err)

        mlogger.debug('Link button assembly.class: %s.%s',
                      self.assembly, self.command_class)


class InvokeButton(GenericUICommand):
    type_id = exts.INVOKE_BUTTON_POSTFIX

    def __init__(self):
        GenericUICommand.__init__(self)
        self.assembly = self.command_class = None

    def __init_from_dir__(self, cmd_dir):
        GenericUICommand.__init_from_dir__(self, cmd_dir, needs_script=False)
        self.assembly = self.command_class = None
        if self.meta:
            self.assembly = \
                self.meta.get(exts.MDATA_LINK_BUTTON_ASSEMBLY, None)
            if not self.assembly:
                mlogger.error("Invoke button does not specify target assembly.")

            self.command_class = \
                self.meta.get(exts.MDATA_LINK_BUTTON_COMMAND_CLASS, None)

            # assign the metadata file to the script
            self.script_file = self.config_script_file = self.meta_file
        else:
            mlogger.error("Invoke button does not have any bundle metadata.")

        self._verify_target()
        mlogger.debug('Invoke button assembly.class: %s.%s',
                      self.assembly, self.command_class)

    def _verify_target(self):
        # verify dll exists
        if self.assembly and not op.exists(self.assembly):
            self.assembly = self.get_bundle_file(self.assembly)
            if not op.exists(self.assembly):
                mlogger.error(
                    'Command %s: Can not determine target dll from: %s',
                    self, self.assembly)
                raise PyRevitException()


class PushButton(GenericUICommand):
    type_id = exts.PUSH_BUTTON_POSTFIX


class PanelPushButton(GenericUICommand):
    type_id = exts.PANEL_PUSH_BUTTON_POSTFIX


class ToggleButton(GenericUICommand):
    type_id = exts.TOGGLE_BUTTON_POSTFIX

    def __init__(self):
        GenericUICommand.__init__(self)
        self.icon_on_file = self.icon_off_file = None
        if self.name:
            mlogger.deprecate('{} | Toggle bundle is deprecated and will be '
                              'removed soon. Please use SmartButton bundle, '
                              'or any other bundle and use script.toggle_icon '
                              'method to toggle the tool icon.'
                              .format(self.name))

    def __init_from_dir__(self, cmd_dir):
        GenericUICommand.__init_from_dir__(self, cmd_dir)

        full_file_path = op.join(self.directory, exts.DEFAULT_ON_ICON_FILE)
        self.icon_on_file = \
            full_file_path if op.exists(full_file_path) else None

        full_file_path = op.join(self.directory, exts.DEFAULT_OFF_ICON_FILE)
        self.icon_off_file = \
            full_file_path if op.exists(full_file_path) else None

        if self.name:
            mlogger.deprecate('{} | Toggle bundle is deprecated and will be '
                              'removed soon. Please use SmartButton bundle, '
                              'or any other bundle and use script.toggle_icon '
                              'method to toggle the tool icon.'
                              .format(self.name))


class SmartButton(GenericUICommand):
    type_id = exts.SMART_BUTTON_POSTFIX


# Command groups only include commands. these classes can include
# GenericUICommand as sub components
class GenericUICommandGroup(GenericUIContainer):
    allowed_sub_cmps = [GenericUICommand]

    def has_commands(self):
        for component in self:
            if component.is_valid_cmd():
                return True


class PullDownButtonGroup(GenericUICommandGroup):
    type_id = exts.PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericUICommandGroup):
    type_id = exts.SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericUICommandGroup):
    type_id = exts.SPLIT_BUTTON_POSTFIX


# Stacks include GenericUICommand, or GenericUICommandGroup
class GenericStack(GenericUIContainer):
    allowed_sub_cmps = [GenericUICommandGroup, GenericUICommand]

    def has_commands(self):
        for component in self:
            if not component.is_container:
                if component.is_valid_cmd():
                    return True
            else:
                if component.has_commands():
                    return True


class StackThreeButtonGroup(GenericStack):
    type_id = exts.STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericStack):
    type_id = exts.STACKTWO_BUTTON_POSTFIX


# Panels include GenericStack, GenericUICommand, or GenericUICommandGroup
class Panel(GenericUIContainer):
    type_id = exts.PANEL_POSTFIX
    allowed_sub_cmps = [GenericStack, GenericUICommandGroup, GenericUICommand]

    def has_commands(self):
        for component in self:
            if not component.is_container:
                if component.is_valid_cmd():
                    return True
            else:
                if component.has_commands():
                    return True

    def contains(self, item_name):
        # Panels contain stacks. But stacks itself does not have any ui and its
        # subitems are displayed within the ui of the parent panel.
        # This is different from pulldowns and other button groups.
        # Button groups, contain and display their sub components in their
        # own drop down menu. So when checking if panel has a button,
        # panel should check all the items visible to the user and respond.
        item_exists = GenericUIContainer.contains(self, item_name)
        if item_exists:
            return True
        else:
            # if child is a stack item, check its children too
            for component in self._sub_components:
                if isinstance(component, GenericStack) \
                        and component.contains(item_name):
                    return True


# Tabs include Panels
class Tab(GenericUIContainer):
    type_id = exts.TAB_POSTFIX
    allowed_sub_cmps = [Panel]

    def has_commands(self):
        for panel in self:
            if panel.has_commands():
                return True
        return False


# UI Tools extension class
# ------------------------------------------------------------------------------
class Extension(GenericUIContainer):
    type_id = exts.ExtensionTypes.UI_EXTENSION.POSTFIX
    allowed_sub_cmps = [Tab]

    def __init__(self):
        GenericUIContainer.__init__(self)
        self.author = None
        self.version = None
        self.pyrvt_version = self.dir_hash_value = None

    def __init_from_dir__(self, package_dir):   #pylint: disable=W0221
        GenericUIContainer.__init_from_dir__(self, package_dir)
        self.pyrvt_version = get_pyrevit_version().get_formatted()

        self.dir_hash_value = self._read_dir_hash()
        if not self.dir_hash_value:
            self.dir_hash_value = self._calculate_extension_dir_hash()

    @property
    def hash_cache(self):
        hash_file = op.join(self.directory, exts.EXTENSION_HASH_CACHE_FILENAME)
        if op.isfile(hash_file):
            return hash_file
        else:
            return ''

    @property
    def ext_hash_value(self):
        return coreutils.get_str_hash(safe_strtype(self.get_cache_data()))

    # def _write_dir_hash(self, hash_value):
    #     if os.access(self.hash_cache, os.W_OK):
    #         try:
    #             with open(self.hash_cache, 'w') as hash_file:
    #                 hash_file.writeline(hash_value)
    #                 return True
    #         except Exception:
    #             return False
    #     return False

    def _read_dir_hash(self):
        if self.hash_cache:
            try:
                with open(self.hash_cache, 'r') as hash_file:
                    return hash_file.readline().rstrip()
            except Exception:
                return ''
        else:
            return ''

    def _calculate_extension_dir_hash(self):
        """Creates a unique hash # to represent state of directory."""
        # search does not include png files:
        #   if png files are added the parent folder mtime gets affected
        #   cache only saves the png address and not the contents so they'll
        #   get loaded everytime
        #       see http://stackoverflow.com/a/5141710/2350244
        pat = '(\\' + exts.TAB_POSTFIX + ')|(\\' + exts.PANEL_POSTFIX + ')'
        pat += '|(\\' + exts.PULLDOWN_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.SPLIT_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.SPLITPUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.STACKTWO_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.STACKTHREE_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.PUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.SMART_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.TOGGLE_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.LINK_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.PANEL_PUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.NOGUI_COMMAND_POSTFIX + ')'
        # tnteresting directories
        pat += '|(\\' + exts.COMP_LIBRARY_DIR_NAME + ')'
        # search for scripts, setting files (future support), and layout files
        patfile = '(\\' + exts.PYTHON_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.CSHARP_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.VB_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.RUBY_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.DYNAMO_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.GRASSHOPPER_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.YAML_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.JSON_FILE_FORMAT + ')'
        patfile += '|(' + exts.DEFAULT_LAYOUT_FILE_NAME + ')'
        return coreutils.calculate_dir_hash(self.directory, pat, patfile)

    def get_all_commands(self):
        return self.get_components_of_type(GenericUICommand)

    def get_manifest_file(self):
        return self.get_bundle_file(exts.EXT_MANIFEST_FILE)

    def get_manifest(self):
        manifest_file = self.get_manifest_file()
        if manifest_file:
            with codecs.open(manifest_file, 'r', 'utf-8') as mfile:
                try:
                    manifest_cfg = json.load(mfile)
                    return manifest_cfg
                except Exception as manfload_err:
                    print('Can not parse ext manifest file: {} '
                          '| {}'.format(manifest_file, manfload_err))
                    return

    def configure(self):
        cfg_dict = self.get_manifest()
        if cfg_dict:
            for cmd in self.get_all_commands():
                cmd.configure(cfg_dict)

    @property
    def startup_script(self):
        return self.get_bundle_file(exts.EXT_STARTUP_FILE)


# library extension class
# ------------------------------------------------------------------------------
class LibraryExtension(GenericComponent):
    type_id = exts.ExtensionTypes.LIB_EXTENSION.POSTFIX

    def __init__(self):
        GenericComponent.__init__(self)
        self.directory = None

    def __init_from_dir__(self, ext_dir):
        if not ext_dir.endswith(self.type_id):
            raise PyRevitException('Can not initialize from directory: {}'
                                   .format(ext_dir))
        self.directory = ext_dir
        self.name = op.splitext(op.basename(self.directory))[0]

    def __repr__(self):
        return '<type_id \'{}\' name \'{}\' @ \'{}\'>'\
            .format(self.type_id, self.name, self.directory)
