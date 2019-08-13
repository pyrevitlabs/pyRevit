from pyrevit.coreutils.runtime import ScriptOutputManager


__context__ = 'zerodoc'


from pyrevit import EXEC_PARAMS
for engine_id in EXEC_PARAMS.engine_mgr.EngineDict:
    print(engine_id)

print('Running in reused engine?\n{}'
      .format('Yes' if __cachedengine__ else 'No'))


for so in ScriptOutputManager.ActiveOutputWindows:
    print(so.OutputId, so.OutputUniqueId)
