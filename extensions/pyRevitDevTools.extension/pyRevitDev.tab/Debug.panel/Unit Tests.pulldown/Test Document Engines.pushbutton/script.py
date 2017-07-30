__context__ = 'zerodoc'


from pyrevit import EXEC_PARAMS
for engine_id in EXEC_PARAMS.engine_mgr.EngineDict:
    print(engine_id)

print(__cachedengine__)