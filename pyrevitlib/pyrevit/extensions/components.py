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
        self.assembly = self.command_class = self.avail_command_class = None
        # read metadata from metadata file
        if self.meta:
            # get the target assembly from metadata
            self.assembly = \
                self.meta.get(exts.MDATA_LINK_BUTTON_ASSEMBLY, None)

            # get the target command class from metadata
            self.command_class = \
                self.meta.get(exts.MDATA_LINK_BUTTON_COMMAND_CLASS, None)

            # get the target command class from metadata
            self.avail_command_class = \
                self.meta.get(exts.MDATA_LINK_BUTTON_AVAIL_COMMAND_CLASS, None)

            # for invoke buttons there is no script source so
            # assign the metadata file to the script
            self.script_file = self.config_script_file = self.meta_file
        else:
            mlogger.debug("%s does not specify target assembly::class.", self)

        if self.directory and not self.assembly:
            mlogger.error("%s does not specify target assembly.", self)

        if self.directory and needs_commandclass and not self.command_class:
            mlogger.error("%s does not specify target command class.", self)

        mlogger.debug('%s assembly.class: %s.%s',
                      self, self.assembly, self.command_class)

    def get_target_assembly(self, required=False):
        assm_file = self.assembly.lower()
        if not assm_file.endswith(framework.ASSEMBLY_FILE_TYPE):
            assm_file += '.' + framework.ASSEMBLY_FILE_TYPE

        # try finding assembly for this specific host version
        target_asm_by_host = self.find_bundle_module(assm_file, by_host=True)
        if target_asm_by_host:
            return target_asm_by_host
        # try find assembly by its name
        target_asm = self.find_bundle_module(assm_file)
        if target_asm:
            return target_asm

        if required:
            mlogger.error("%s can not find target assembly.", self)

        return ''


class LinkButton(NoScriptButton):
    type_id = exts.LINK_BUTTON_POSTFIX

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        NoScriptButton.__init__(
            self,
            cmp_path=cmp_path,
            needs_commandclass=True
            )

        if self.context:
            mlogger.warn(
                "Linkbutton bundles do not support \"context:\". "
                "Use \"availability_class:\" instead and specify name of "
                "availability class in target assembly | %s", self
                )
            self.context = None


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
        if self.directory and not self.script_file:
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


class URLButton(GenericUICommand):
    type_id = exts.URL_BUTTON_POSTFIX

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        GenericUICommand.__init__(self, cmp_path=cmp_path, needs_script=False)
        self.target_url = None
        # read metadata from metadata file
        if self.meta:
            # get the target url from metadata
            self.target_url = \
                self.meta.get(exts.MDATA_URL_BUTTON_HYPERLINK, None)
            # for url buttons there is no script source so
            # assign the metadata file to the script
            self.script_file = self.config_script_file = self.meta_file
        else:
            mlogger.debug("%s does not specify target assembly::class.", self)

        if self.directory and not self.target_url:
            mlogger.error("%s does not specify target url.", self)

        mlogger.debug('%s target url: %s', self, self.target_url)

    def get_target_url(self):
        return self.target_url or ""


# Command groups only include commands. these classes can include
# GenericUICommand as sub components
class GenericUICommandGroup(GenericUIContainer):
    allowed_sub_cmps = [GenericUICommand, NoScriptButton]

    @property
    def control_id(self):
        # stacks don't have control id
        if self.parent_ctrl_id:
            deepend_parent_id = self.parent_ctrl_id.replace(
                '_%CustomCtrl',
                '_%CustomCtrl_%CustomCtrl'
            )
            return deepend_parent_id + '%{}'.format(self.name)
        else:
            return '%{}%'.format(self.name)

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

    @property
    def control_id(self):
        # stacks don't have control id
        return self.parent_ctrl_id if self.parent_ctrl_id else ''

    def has_commands(self):
        for component in self:
            if not component.is_container:
                if isinstance(component, GenericUICommand):
                    return True
            else:
                if component.has_commands():
                    return True


class StackButtonGroup(GenericStack):
    type_id = exts.STACK_BUTTON_POSTFIX



# Panels include GenericStack, GenericUICommand, or GenericUICommandGroup
class Panel(GenericUIContainer):
    type_id = exts.PANEL_POSTFIX
    allowed_sub_cmps = \
        [GenericStack, GenericUICommandGroup, GenericUICommand, NoScriptButton]

    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        GenericUIContainer.__init__(self, cmp_path=cmp_path)
        self.panel_background = \
            self.title_background = \
                self.slideout_background = None
        # read metadata from metadata file
        if self.meta:
            # check for background color configs
            self.panel_background = \
                self.meta.get(exts.MDATA_BACKGROUND_KEY, None)
            if self.panel_background:
                if isinstance(self.panel_background, dict):
                    self.title_background = self.panel_background.get(
                        exts.MDATA_BACKGROUND_TITLE_KEY, None)
                    self.slideout_background = self.panel_background.get(
                        exts.MDATA_BACKGROUND_SLIDEOUT_KEY, None)
                    self.panel_background = self.panel_background.get(
                        exts.MDATA_BACKGROUND_PANEL_KEY, None)
                elif not isinstance(self.panel_background, str):
                    mlogger.error(
                        "%s bad background definition in metadata.", self)

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
        pat += '|(\\' + exts.COMP_HOOKS_DIR_NAME + ')'
        # search for scripts, setting files (future support), and layout files
        patfile = '(\\' + exts.PYTHON_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.CSHARP_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.VB_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.RUBY_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.DYNAMO_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.GRASSHOPPER_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.GRASSHOPPERX_SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.CONTENT_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.YAML_FILE_FORMAT + ')'
        patfile += '|(\\' + exts.JSON_FILE_FORMAT + ')'
        return coreutils.calculate_dir_hash(self.directory, pat, patfile)

    def _update_from_directory(self):   #pylint: disable=W0221
        # using classname otherwise exceptions in superclasses won't show
        GenericUIContainer._update_from_directory(self)
        self.pyrvt_version = versionmgr.get_pyrevit_version().get_formatted()

        # extensions can store event hooks under
        # hooks/ inside the component folder
        hooks_path = op.join(self.directory, exts.COMP_HOOKS_DIR_NAME)
        self.hooks_path = hooks_path if op.exists(hooks_path) else None

        # extensions can store preflight checks under
        # checks/ inside the component folder
        checks_path = op.join(self.directory, exts.COMP_CHECKS_DIR_NAME)
        self.checks_path = checks_path if op.exists(checks_path) else None

        self.dir_hash_value = self._calculate_extension_dir_hash()

    @property
    def control_id(self):
        return None

    @property
    def startup_script(self):
        return self.find_bundle_file([
            exts.PYTHON_EXT_STARTUP_FILE,
            exts.CSHARP_EXT_STARTUP_FILE,
            exts.VB_EXT_STARTUP_FILE,
            exts.RUBY_EXT_STARTUP_FILE,
        ])

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

    def get_extension_modules(self):
        modules = []
        if self.binary_path and op.exists(self.binary_path):
            for item in os.listdir(self.binary_path):
                item_path = op.join(self.binary_path, item)
                item_name = item.lower()
                if op.isfile(item_path) \
                        and item_name.endswith(framework.ASSEMBLY_FILE_TYPE):
                    modules.append(item_path)
        return modules

    def get_command_modules(self):
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

    def get_checks(self):
        check_scripts = os.listdir(self.checks_path) if self.checks_path else []
        return [op.join(self.checks_path, x) for x in check_scripts]


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
