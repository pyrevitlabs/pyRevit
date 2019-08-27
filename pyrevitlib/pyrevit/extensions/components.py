"""Base classes for pyRevit extension components."""
import os
import os.path as op
import json
import codecs

from pyrevit import PyRevitException, HOST_APP
from pyrevit.compat import safe_strtype
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts
from pyrevit.extensions.genericcomps import GenericComponent
from pyrevit.extensions.genericcomps import GenericUIContainer
from pyrevit.extensions.genericcomps import GenericUICommand
from pyrevit import versionmgr


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


EXT_HASH_VALUE_KEY = 'dir_hash_value'
EXT_HASH_VERSION_KEY = 'pyrvt_version'


# Derived classes here correspond to similar elements in Revit ui.
# Under Revit UI:
# Packages contain Tabs, Tabs contain, Panels, Panels contain Stacks,
# Commands, or Command groups
# ------------------------------------------------------------------------------
class NoButton(GenericUICommand):
    type_id = exts.NOGUI_COMMAND_POSTFIX


class NoScriptButton(GenericUICommand):
    def __init__(self, cmp_path=None, needs_commandclass=False):
        # using classname otherwise exceptions in superclasses won't show
        GenericUICommand.__init__(self, cmp_path=cmp_path, needs_script=False)
        self.assembly = self.command_class = None
        # to support legacy linkbutton types using python global var convention
        # if has python script, read metadata
        if self.script_language == exts.PYTHON_LANG:
            try:
                # reading script file content to extract parameters
                script_content = \
                    coreutils.ScriptFileParser(self.script_file)

                self.assembly = \
                    script_content.extract_param(exts.LINK_BUTTON_ASSEMBLY)

                self.command_class = \
                    script_content.extract_param(exts.LINK_BUTTON_COMMAND_CLASS)

                if self.assembly or self.command_class:
                    mlogger.deprecate(
                        "Creating link buttons using \"__assembly__\" "
                        "and \"__commandclass__\" global "
                        "variables inside a python file is deprecated. "
                        "use bundle.yaml instead. | %s", self)

            except PyRevitException as err:
                mlogger.error(err)

        # otherwise read metadata from metadata file
        elif self.meta:
            # get the target assembly from metadata
            self.assembly = \
                self.meta.get(exts.MDATA_LINK_BUTTON_ASSEMBLY, None)

            # get the target command class from metadata
            self.command_class = \
                self.meta.get(exts.MDATA_LINK_BUTTON_COMMAND_CLASS, None)

            # for invoke buttons there is no script source so
            # assign the metadata file to the script
            self.script_file = self.config_script_file = self.meta_file
        else:
            mlogger.debug("%s does not specify target assembly::class.", self)

        if not self.assembly:
            mlogger.error("%s does not specify target assembly.", self)

        if needs_commandclass and not self.command_class:
            mlogger.error("%s does not specify target command class.", self)

        mlogger.debug('%s assembly.class: %s.%s',
                      self, self.assembly, self.command_class)

    def get_target_assembly(self, required=False):
        assm_file = self.assembly.lower()
        if not assm_file.endswith(framework.ASSEMBLY_FILE_TYPE):
            assm_file += '.' + framework.ASSEMBLY_FILE_TYPE
        target_asm = self.find_bundle_module(assm_file)
        if not target_asm and required:
            mlogger.error("%s can not find target assembly.", self)
        return target_asm or ''


class LinkButton(NoScriptButton):
    type_id = exts.LINK_BUTTON_POSTFIX

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        NoScriptButton.__init__(
            self,
            cmp_path=cmp_path,
            needs_commandclass=True
            )


class InvokeButton(NoScriptButton):
    type_id = exts.INVOKE_BUTTON_POSTFIX

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        NoScriptButton.__init__(self, cmp_path=cmp_path)


class PushButton(GenericUICommand):
    type_id = exts.PUSH_BUTTON_POSTFIX


class PanelPushButton(GenericUICommand):
    type_id = exts.PANEL_PUSH_BUTTON_POSTFIX


class SmartButton(GenericUICommand):
    type_id = exts.SMART_BUTTON_POSTFIX


class ContentButton(GenericUICommand):
    type_id = exts.CONTENT_BUTTON_POSTFIX

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        GenericUICommand.__init__(
            self,
            cmp_path=cmp_path,
            needs_script=False
            )
        # find content file
        self.script_file = \
            self.find_bundle_file([
                exts.CONTENT_VERSION_POSTFIX.format(
                    version=HOST_APP.version
                    ),
                ])
        if not self.script_file:
            self.script_file = \
                self.find_bundle_file([
                    exts.CONTENT_POSTFIX,
                    ])
        # requires at least one bundles
        if not self.script_file:
            mlogger.error('Command %s: Does not have content file.', self)
            self.script_file = ''

        # find alternative content file
        self.config_script_file = \
            self.find_bundle_file([
                exts.ALT_CONTENT_VERSION_POSTFIX.format(
                    version=HOST_APP.version
                    ),
                ])
        if not self.config_script_file:
            self.config_script_file = \
                self.find_bundle_file([
                    exts.ALT_CONTENT_POSTFIX,
                    ])
        if not self.config_script_file:
            self.config_script_file = ''


# Command groups only include commands. these classes can include
# GenericUICommand as sub components
class GenericUICommandGroup(GenericUIContainer):
    allowed_sub_cmps = [GenericUICommand, NoScriptButton]

    def has_commands(self):
        for component in self:
            if isinstance(component, GenericUICommand):
                return True


class PullDownButtonGroup(GenericUICommandGroup):
    type_id = exts.PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericUICommandGroup):
    type_id = exts.SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericUICommandGroup):
    type_id = exts.SPLIT_BUTTON_POSTFIX


# Stacks include GenericUICommand, or GenericUICommandGroup
class GenericStack(GenericUIContainer):
    type_id = exts.STACK_BUTTON_POSTFIX

    allowed_sub_cmps = \
        [GenericUICommandGroup, GenericUICommand, NoScriptButton]

    def has_commands(self):
        for component in self:
            if not component.is_container:
                if isinstance(component, GenericUICommand):
                    return True
            else:
                if component.has_commands():
                    return True


# Panels include GenericStack, GenericUICommand, or GenericUICommandGroup
class Panel(GenericUIContainer):
    type_id = exts.PANEL_POSTFIX
    allowed_sub_cmps = \
        [GenericStack, GenericUICommandGroup, GenericUICommand, NoScriptButton]

    def has_commands(self):
        for component in self:
            if not component.is_container:
                if isinstance(component, GenericUICommand):
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
            for component in self:
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

    def __init__(self, cmp_path=None):
        self.pyrvt_version = None
        self.dir_hash_value = None
        # using classname otherwise exceptions in superclasses won't show
        GenericUIContainer.__init__(self, cmp_path=cmp_path)

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
        pat += '|(\\' + exts.STACK_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.PUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.SMART_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.LINK_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.PANEL_PUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.PANEL_PUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + exts.CONTENT_BUTTON_POSTFIX + ')'
        # tnteresting directories
        pat += '|(\\' + exts.COMP_LIBRARY_DIR_NAME + ')'
        # search for scripts, setting files (future support), and layout files
        patfile = '(\\' + exts.PYTHON_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.CSHARP_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.VB_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.RUBY_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.DYNAMO_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.GRASSHOPPER_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.CONTENT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.YAML_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.JSON_FILE_FORMAT + ')'
        patfile += '|(' + exts.DEFAULT_LAYOUT_FILE_NAME + ')'
        return coreutils.calculate_dir_hash(self.directory, pat, patfile)

    def _update_from_directory(self):   #pylint: disable=W0221
        # using classname otherwise exceptions in superclasses won't show
        GenericUIContainer._update_from_directory(self)
        self.pyrvt_version = versionmgr.get_pyrevit_version().get_formatted()

        # extensions can store event hooks under
        # hooks/ inside the component folder
        hooks_path = op.join(self.directory, exts.COMP_HOOKS_DIR_NAME)
        self.hooks_path = hooks_path if op.exists(hooks_path) else None

        self.dir_hash_value = self._calculate_extension_dir_hash()

    @property
    def startup_script(self):
        return self.get_bundle_file(exts.EXT_STARTUP_FILE)

    def get_hash(self):
        return coreutils.get_str_hash(safe_strtype(self.get_cache_data()))

    def get_all_commands(self):
        return self.find_components_of_type(GenericUICommand)

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
            for component in self:
                component.configure(cfg_dict)

    def get_all_modules(self):
        referenced_modules = set()
        for cmd in self.get_all_commands():
            for module in cmd.modules:
                cmd_module = cmd.find_bundle_module(module)
                if cmd_module:
                    referenced_modules.add(cmd_module)
        return referenced_modules

    def get_hooks(self):
        hook_scripts = os.listdir(self.hooks_path) if self.hooks_path else []
        return [op.join(self.hooks_path, x) for x in hook_scripts]


# library extension class
# ------------------------------------------------------------------------------
class LibraryExtension(GenericComponent):
    type_id = exts.ExtensionTypes.LIB_EXTENSION.POSTFIX

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        GenericComponent.__init__(self)
        self.directory = cmp_path

        if self.directory:
            self.name = op.splitext(op.basename(self.directory))[0]

    def __repr__(self):
        return '<type_id \'{}\' name \'{}\' @ \'{}\'>'\
            .format(self.type_id, self.name, self.directory)

    @classmethod
    def matches(cls, component_path):
        return component_path.lower().endswith(cls.type_id)
