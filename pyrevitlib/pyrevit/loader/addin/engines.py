from pyrevit import HOME_DIR
from pyrevit.labs import TargetApps


def set_engines(engine_ver):
    pass


def get_engines():
    return TargetApps.Revit.PyRevitClone.GetEngines(HOME_DIR)


def get_engine(engine_ver):
    return TargetApps.Revit.PyRevitClone.GetEngine(HOME_DIR, engine_ver)


def get_latest_engine():
    return TargetApps.Revit.PyRevitClone.GetEngine(HOME_DIR)