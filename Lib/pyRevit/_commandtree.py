import os
import os.path as op
import sys

from .exceptions import *
from .logger import logger
from .config import PACKAGE_POSTFIX, TAB_POSTFIX, PANEL_POSTFIX, LINK_BUTTON_POSTFIX


# generic private superclasses -----------------------------------------------------------------------------------------

# superclass for all tree branches that contain sub-branches
class _GenericTreeBranch:
    def __init__(self):
        self.name = None
        self.branch_type = None
        self.sub_branches = None


# superclass for all single commands.
class _GenericCommand:
    def __init__(self):
        self.name = None
        self.script_file = None
        self.command_type = None
        self.icon = None


# superclass for all groups of commands.
class _GenericCommandGroup:
    def __init__(self):
        self.icon = None


# public tree classes --------------------------------------------------------------------------------------------------

# root class for each package. might contain multiple tabs
class Package(_GenericTreeBranch):
    def __init__(self):
        _GenericTreeBranch.__init__(self)
        self.branch_type = PACKAGE_POSTFIX


# class for each tab. might contain multiple panels
class Tab(_GenericTreeBranch):
    def __init__(self):
        _GenericTreeBranch.__init__(self)
        self.branch_type = TAB_POSTFIX


# class for each panel. might contain commands or command groups
class Panel(_GenericTreeBranch):
    def __init__(self):
        _GenericTreeBranch.__init__(self)
        self.branch_type = PANEL_POSTFIX


class LinkButton(_GenericCommand):
    def __init__(self):
        _GenericCommand.__init__(self)
        self.command_type = LINK_BUTTON_POSTFIX
