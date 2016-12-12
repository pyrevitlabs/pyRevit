import os.path as op

from pyrevit import PyRevitException
from pyrevit.coreutils import ScriptFileParser, calculate_dir_hash, get_str_hash
from pyrevit.coreutils.logger import get_logger
from pyrevit.extensions import LINK_BUTTON_POSTFIX, LINK_BUTTON_ASSEMBLY_PARAM, LINK_BUTTON_COMMAND_CLASS_PARAM
from pyrevit.extensions import PANEL_POSTFIX, TAB_POSTFIX
from pyrevit.extensions import PULLDOWN_BUTTON_POSTFIX, SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX
from pyrevit.extensions import PUSH_BUTTON_POSTFIX, SMART_BUTTON_POSTFIX
from pyrevit.extensions import SCRIPT_FILE_FORMAT, DEFAULT_LAYOUT_FILE_NAME
from pyrevit.extensions import STACKTWO_BUTTON_POSTFIX, STACKTHREE_BUTTON_POSTFIX
from pyrevit.extensions import TOGGLE_BUTTON_POSTFIX, DEFAULT_ON_ICON_FILE, DEFAULT_OFF_ICON_FILE
from pyrevit.extensions import UI_EXTENSION_POSTFIX, LIB_EXTENSION_POSTFIX
from pyrevit.extensions.genericcomps import GenericComponent, GenericUIContainer, GenericUICommand
from pyrevit.repo import PYREVIT_VERSION

logger = get_logger(__name__)


# Derived classes here correspond to similar elements in Revit ui. Under Revit UI:
# Packages contain Tabs, Tabs contain, Panels, Panels contain Stacks, Commands, or Command groups
# ----------------------------------------------------------------------------------------------------------------------
class LinkButton(GenericUICommand):
    type_id = LINK_BUTTON_POSTFIX

    def __init__(self):
        GenericUICommand.__init__(self)
        self.assembly = self.command_class = None

    def __init_from_dir__(self, cmd_dir):
        GenericUICommand.__init_from_dir__(self, cmd_dir)
        self.assembly = self.command_class = None
        try:
            # reading script file content to extract parameters
            script_content = ScriptFileParser(self.get_full_script_address())
            self.assembly = script_content.extract_param(LINK_BUTTON_ASSEMBLY_PARAM)  # type: str
            self.command_class = script_content.extract_param(LINK_BUTTON_COMMAND_CLASS_PARAM)  # type: str
        except PyRevitException as err:
            logger.error(err)

        logger.debug('Link button assembly.class: {}.{}'.format(self.assembly, self.command_class))


class PushButton(GenericUICommand):
    type_id = PUSH_BUTTON_POSTFIX


class ToggleButton(GenericUICommand):
    type_id = TOGGLE_BUTTON_POSTFIX

    def __init__(self):
        GenericUICommand.__init__(self)
        self.icon_on_file = self.icon_off_file = None

    def __init_from_dir__(self, cmd_dir):
        GenericUICommand.__init_from_dir__(self, cmd_dir)

        full_file_path = op.join(self.directory, DEFAULT_ON_ICON_FILE)
        self.icon_on_file = full_file_path if op.exists(full_file_path) else None

        full_file_path = op.join(self.directory, DEFAULT_OFF_ICON_FILE)
        self.icon_off_file = full_file_path if op.exists(full_file_path) else None


class SmartButton(GenericUICommand):
    type_id = SMART_BUTTON_POSTFIX


# # Command groups only include commands. these classes can include GenericUICommand as sub components
class GenericUICommandGroup(GenericUIContainer):
    allowed_sub_cmps = [GenericUICommand]

    def has_commands(self):
        for component in self:
            if component.is_valid_cmd():
                return True


class PullDownButtonGroup(GenericUICommandGroup):
    type_id = PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericUICommandGroup):
    type_id = SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericUICommandGroup):
    type_id = SPLIT_BUTTON_POSTFIX


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
    type_id = STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericStack):
    type_id = STACKTWO_BUTTON_POSTFIX


# Panels include GenericStack, GenericUICommand, or GenericUICommandGroup
class Panel(GenericUIContainer):
    type_id = PANEL_POSTFIX
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
        # Panels contain stacks. But stacks itself does not have any ui and its subitems are displayed within the ui of
        # the parent panel. This is different from pulldowns and other button groups. Button groups, contain and display
        # their sub components in their own drop down menu.
        # So when checking if panel has a button, panel should check all the items visible to the user and respond.
        item_exists = GenericUIContainer.contains(self, item_name)
        if item_exists:
            return True
        else:
            # if child is a stack item, check its children too
            for component in self._sub_components:
                if isinstance(component, GenericStack) and component.contains(item_name):
                    return True


# Tabs include Panels
class Tab(GenericUIContainer):
    type_id = TAB_POSTFIX
    allowed_sub_cmps = [Panel]

    def has_commands(self):
        for panel in self:
            if panel.has_commands():
                return True
        return False


# UI Tools extension class
# ----------------------------------------------------------------------------------------------------------------------
class Extension(GenericUIContainer):
    type_id = UI_EXTENSION_POSTFIX
    allowed_sub_cmps = [Tab]

    def __init__(self):
        GenericUIContainer.__init__(self)
        self.author = None
        self.version = None
        self.pyrvt_version = self.dir_hash_value = None

    def __init_from_dir__(self, package_dir):
        GenericUIContainer.__init_from_dir__(self, package_dir)
        self.pyrvt_version = PYREVIT_VERSION.get_formatted()
        self.dir_hash_value = self._calculate_extension_dir_hash()

    @property
    def ext_hash_value(self):
        return get_str_hash(str(self.get_cache_data()))

    def _calculate_extension_dir_hash(self):
        """Creates a unique hash # to represent state of directory."""
        # search does not include png files:
        #   if png files are added the parent folder mtime gets affected
        #   cache only saves the png address and not the contents so they'll get loaded everytime
        #       see http://stackoverflow.com/a/5141710/2350244
        pat = '(\\' + TAB_POSTFIX + ')|(\\' + PANEL_POSTFIX + ')'
        pat += '|(\\' + PULLDOWN_BUTTON_POSTFIX + ')'
        pat += '|(\\' + SPLIT_BUTTON_POSTFIX + ')'
        pat += '|(\\' + SPLITPUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + STACKTWO_BUTTON_POSTFIX + ')'
        pat += '|(\\' + STACKTHREE_BUTTON_POSTFIX + ')'
        pat += '|(\\' + PUSH_BUTTON_POSTFIX + ')'
        pat += '|(\\' + SMART_BUTTON_POSTFIX + ')'
        pat += '|(\\' + TOGGLE_BUTTON_POSTFIX + ')'
        pat += '|(\\' + LINK_BUTTON_POSTFIX + ')'
        # seach for scripts, setting files (future support), and layout files
        patfile = '(\\' + SCRIPT_FILE_FORMAT + ')'
        patfile += '|(' + DEFAULT_LAYOUT_FILE_NAME + ')'
        return calculate_dir_hash(self.directory, pat, patfile)


# library extension class
# ----------------------------------------------------------------------------------------------------------------------
class LibraryExtension(GenericComponent):
    type_id = LIB_EXTENSION_POSTFIX

    def __init__(self):
        GenericComponent.__init__(self)
        self.directory = None

    def __init_from_dir__(self, ext_dir):
        if not ext_dir.endswith(self.type_id):
            raise PyRevitException('Can not initialize from directory: {}'.format(ext_dir))
        self.directory = ext_dir
        self.name = op.splitext(op.basename(self.directory))[0]
