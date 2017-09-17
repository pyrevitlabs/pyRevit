from pyrevit import EXEC_PARAMS
from pyrevit.platform import clr
from pyrevit.coreutils.logger import get_logger

clr.AddReference('IronPython.dll')

# noinspection PyUnresolvedReferences
import IronPython


logger = get_logger(__name__)


class IPyEngineWrapper:
    def __init__(self, engine_ref):
        self.engine = engine_ref

    @property
    def name(self):
        return self.engine.Setup.DisplayName

    @property
    def sys_module(self):
        return IronPython.Hosting.Python.GetSysModule(self.engine)

    @property
    def builtin_module(self):
        return IronPython.Hosting.Python.GetBuiltinModule(self.engine)

    @property
    def path(self):
        return list(self.engine.GetSearchPaths())

    @path.setter
    def path(self, path_list):
        self.engine.SetSearchPaths(path_list)


def get_engine_wrapper():
    return IPyEngineWrapper(EXEC_PARAMS.engine)
