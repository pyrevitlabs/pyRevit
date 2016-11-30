import hashlib
import os
import os.path as op
import re

from pyrevit.core.logger import get_logger


logger = get_logger(__name__)


# Derived classes here correspond to similar elements in Revit ui. Under Revit UI:
# Packages contain Tabs, Tabs contain, Panels, Panels contain Stacks, Commands, or Command groups
# ----------------------------------------------------------------------------------------------------------------------
class LinkButton(GenericCommand):
    type_id = LINK_BUTTON_POSTFIX

    def __init__(self):
        GenericCommand.__init__(self)
        self.assembly = self.command_class = None

    def __init_from_dir__(self, cmd_dir):
        GenericCommand.__init_from_dir__(self, cmd_dir)
        self.assembly = self.command_class = None
        try:
            # reading script file content to extract parameters
            script_content = ScriptFileParser(self.get_full_script_address())
            self.assembly = script_content.extract_param(LINK_BUTTON_ASSEMBLY_PARAM)  # type: str
            self.command_class = script_content.extract_param(LINK_BUTTON_COMMAND_CLASS_PARAM)  # type: str
        except PyRevitException as err:
            logger.error(err)

        logger.debug('Link button assembly.class: {}.{}'.format(self.assembly, self.command_class))


class PushButton(GenericCommand):
    type_id = PUSH_BUTTON_POSTFIX


class ToggleButton(GenericCommand):
    type_id = TOGGLE_BUTTON_POSTFIX

    def __init__(self):
        GenericCommand.__init__(self)
        self.icon_on_file = self.icon_off_file = None

    def __init_from_dir__(self, cmd_dir):
        GenericCommand.__init_from_dir__(self, cmd_dir)

        full_file_path = op.join(self.directory, DEFAULT_ON_ICON_FILE)
        self.icon_on_file = full_file_path if op.exists(full_file_path) else None

        full_file_path = op.join(self.directory, DEFAULT_OFF_ICON_FILE)
        self.icon_off_file = full_file_path if op.exists(full_file_path) else None


class SmartButton(GenericCommand):
    type_id = SMART_BUTTON_POSTFIX


# # Command groups only include commands. these classes can include GenericCommand as sub components
class GenericCommandGroup(GenericContainer):
    allowed_sub_cmps = [GenericCommand]

    def has_commands(self):
        for component in self:
            if component.is_valid_cmd():
                return True


class PullDownButtonGroup(GenericCommandGroup):
    type_id = PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericCommandGroup):
    type_id = SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericCommandGroup):
    type_id = SPLIT_BUTTON_POSTFIX


# Stacks include GenericCommand, or GenericCommandGroup
class GenericStack(GenericContainer):
    allowed_sub_cmps = [GenericCommandGroup, GenericCommand]

    def has_commands(self):
        for component in self:
            if not component.is_container():
                if component.is_valid_cmd():
                    return True
            else:
                if component.has_commands():
                    return True


class StackThreeButtonGroup(GenericStack):
    type_id = STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericStack):
    type_id = STACKTWO_BUTTON_POSTFIX


# Panels include GenericStack, GenericCommand, or GenericCommandGroup
class Panel(GenericContainer):
    type_id = PANEL_POSTFIX
    allowed_sub_cmps = [GenericStack, GenericCommandGroup, GenericCommand]

    def has_commands(self):
        for component in self:
            if not component.is_container():
                if component.is_valid_cmd():
                    return True
            else:
                if component.has_commands():
                    return True

    def contains(self, item_name):
        # Panels contain stacks. But stacks itself does not have any ui and its subitems are displayed within the ui of
        # the prent panel. This is different from pulldowns and other button groups. Button groups, contain and display
        # their sub components in their own drop down menu.
        # So when checking if panel has a button, panel should check all the items visible to the user and respond.
        item_exists = GenericContainer.contains(self, item_name)
        if item_exists:
            return True
        else:
            # if child is a stack item, check its children too
            for component in self._sub_components:
                if isinstance(component, GenericStack) and component.contains(item_name):
                    return True


# Tabs include Panels
class Tab(GenericContainer):
    type_id = TAB_POSTFIX
    allowed_sub_cmps = [Panel]

    def has_commands(self):
        for panel in self:
            if panel.has_commands():
                return True
        return False


# UI Tools extension class
# ----------------------------------------------------------------------------------------------------------------------
class Extension(GenericContainer):
    type_id = PACKAGE_POSTFIX
    allowed_sub_cmps = [Tab]

    def __init__(self):
        GenericContainer.__init__(self)
        self.author = None
        self.version = None
        self.hash_value = self.hash_version = None

    def __init_from_dir__(self, package_dir):
        GenericContainer.__init_from_dir__(self, package_dir)
        self.hash_value = self._calculate_hash()
        self.hash_version = PyRevitVersion.get_formatted()

    def _calculate_hash(self):
        """Creates a unique hash # to represent state of directory."""
        # search does not include png files:
        #   if png files are added the parent folder mtime gets affected
        #   cache only saves the png address and not the contents so they'll get loaded everytime
        #       see http://stackoverflow.com/a/5141710/2350244
        pat = '(\\' + TAB_POSTFIX + ')|(\\' + PANEL_POSTFIX + ')'
        # seach for scripts, setting files (future support), and layout files
        patfile = '(\\' + SCRIPT_FILE_FORMAT + ')'
        patfile += '|(\\' + SETTINGS_FILE_EXTENSION + ')'
        patfile += '|(' + DEFAULT_LAYOUT_FILE_NAME + ')'
        mtime_sum = 0
        for root, dirs, files in os.walk(self.directory):
            if re.search(pat, op.basename(root), flags=re.IGNORECASE):
                mtime_sum += op.getmtime(root)
                for filename in files:
                    if re.search(patfile, filename, flags=re.IGNORECASE):
                        modtime = op.getmtime(op.join(root, filename))
                        mtime_sum += modtime
        return hashlib.md5(str(mtime_sum).encode('utf-8')).hexdigest()


# library extension class
# ----------------------------------------------------------------------------------------------------------------------
class LibraryExtension:
    type_id = LIB_PACKAGE_POSTFIX

    def __init__(self):
        self.directory = None
        self.name = None

    def __init_from_dir__(self, ext_dir):
        self.directory = ext_dir
        if not self.directory.endswith(self.type_id):
            raise PyRevitUnknownFormatError()

        self.name = op.splitext(op.basename(self.directory))[0]
