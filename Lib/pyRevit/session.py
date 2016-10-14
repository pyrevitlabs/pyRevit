from .config import HOME_DIR

from ._assemblies import PyRevitCommandsAssembly
from ._parser import PyRevitParser
from ._cache import PyRevitCache
from ._uielements import PyRevitUI


class PyRevitSession:
    """Handles all tasks for the current session.
    User can import this in their script and get information or interact with current session."""
    def __init__(self, home_dir):
        # an instance should be given a home directory
        self.home_dir = home_dir

        self.cmd_tree = None
        self.assembly = None
        self.ui = None

        try:
            # setting up cache and checking validity for home dir
            session_cache = PyRevitCache(self.home_dir)

            if session_cache.is_cache_valid():
                # if valid get the command tree from cache
                self.cmd_tree = session_cache.get_cmd_tree()
            else:
                # otherwise parse home dir and get command tree
                self.cmd_tree = PyRevitParser(self.home_dir).get_cmd_tree()
                session_cache.update_cache(self.cmd_tree)

            if self.cmd_tree:
                # if command tree is valid, initiate assembly.
                self.assembly = PyRevitCommandsAssembly()
                # update command tree with assembly information (current assembly, or new)
                self.assembly.update_cmd_tree(self.cmd_tree)
                if not self.assembly.is_pyrevit_already_loaded():
                    # create dll assembly for the discovered commands
                    self.assembly.create_assembly(self.cmd_tree)
                # initiate ui, prepares (doesn't create) a new ui, or accesses current ui if it exists
                self.ui = PyRevitUI()
            # at the end of __init__, user can iteract, with (new, existing) ui, cmd_tree, and assembly
        except:
            # todo handle exceptions
            pass

    def create_ui(self):
        # class initializer only prepares everything for the ui
        # user needs to explicitly call this to create the ui
        self.ui.create(self.cmd_tree)


current_session = PyRevitSession(HOME_DIR)
