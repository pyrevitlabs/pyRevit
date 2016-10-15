import os
import os.path as op
import sys

from .exceptions import PyRevitUnknownFormatError
from .logger import logger
from .config import PACKAGE_POSTFIX, TAB_POSTFIX, PANEL_POSTFIX, LINK_BUTTON_POSTFIX, PUSH_BUTTON_POSTFIX,             \
                    TOGGLE_BUTTON_POSTFIX, PULLDOWN_BUTTON_POSTFIX, STACKTHREE_BUTTON_POSTFIX, STACKTWO_BUTTON_POSTFIX,\
                    SPLIT_BUTTON_POSTFIX, SPLITPUSH_BUTTON_POSTFIX


# tree branch classes (package, tab, panel) ----------------------------------------------------------------------------
# superclass for all tree branches that contain sub-branches
class GenericTreeBranch(object):
    def __init__(self, branch_dir):
        self.directory = branch_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.name = None
        self._sub_components = []

    def _is_valid_dir(self):
        return self.directory.endswith(self.type_id)

    def __iter__(self):
        return iter(self._sub_components)

    def add_component(self, comp):
        self._sub_components.append(comp)


# root class for each package. might contain multiple tabs
class Package(GenericTreeBranch):
    type_id = PACKAGE_POSTFIX

    def __init__(self, package_dir):
        GenericTreeBranch.__init__(self, package_dir)
        self.author = None
        self.version = None


# class for each tab. might contain multiple panels
class Tab(GenericTreeBranch):
    type_id = TAB_POSTFIX

    def __init__(self, tab_dir):
        GenericTreeBranch.__init__(self, tab_dir)
        self.sort_level = 0


# class for each panel. might contain commands or command groups
class Panel(GenericTreeBranch):
    type_id = PANEL_POSTFIX

    def __init__(self, panel_dir):
        GenericTreeBranch.__init__(self, panel_dir)
        self.sort_level = 0


# single command classes (link, push button, toggle button) ------------------------------------------------------------
# superclass for all single commands.
class GenericCommand(object):
    def __init__(self, cmd_dir):
        self.cmd_dir = cmd_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.cmd_name = None
        self.icon_file = None
        self.script_file = None

    def _is_valid_dir(self):
        return self.cmd_dir.endswith(self.type_id)


class LinkButton(GenericCommand):
    type_id = LINK_BUTTON_POSTFIX


class PushButton(GenericCommand):
    type_id = PUSH_BUTTON_POSTFIX


class ToggleButton(GenericCommand):
    type_id = TOGGLE_BUTTON_POSTFIX


# command group classes (puu down, split, split pull down, stack2 and stack3) ------------------------------------------
# superclass for all groups of commands.
class GenericCommandGroup(object):
    def __init__(self, group_dir):
        self.group_dir = group_dir
        if not self._is_valid_dir():
            raise PyRevitUnknownFormatError()

        self.group_name = None
        self.sort_level = 0
        self.icon_file = None

        self._sub_commands = []

    def _is_valid_dir(self):
        return self.group_dir.endswith(self.type_id)

    def __iter__(self):
        return iter(self._sub_commands)

    def add_cmd(self, cmd):
        self._sub_commands.append(cmd)


class PullDownButtonGroup(GenericCommandGroup):
    type_id = PULLDOWN_BUTTON_POSTFIX


class SplitPushButtonGroup(GenericCommandGroup):
    type_id = SPLITPUSH_BUTTON_POSTFIX


class SplitButtonGroup(GenericCommandGroup):
    type_id = SPLIT_BUTTON_POSTFIX


class StackThreeButtonGroup(GenericCommandGroup):
    type_id = STACKTHREE_BUTTON_POSTFIX


class StackTwoButtonGroup(GenericCommandGroup):
    type_id = STACKTWO_BUTTON_POSTFIX
