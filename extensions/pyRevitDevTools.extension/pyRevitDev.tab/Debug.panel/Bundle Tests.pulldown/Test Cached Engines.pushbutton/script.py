from pyrevit.runtime.types import ScriptOutputManager, EngineManager


__context__ = 'zerodoc'


from pyrevit import EXEC_PARAMS
print('Active Engines:')
for engine_id in EngineManager.EngineDict:
    print(engine_id)

print('Running in cached engine?\n{}'
      .format('Yes' if __cachedengine__ else 'No'))


for so in ScriptOutputManager.ActiveOutputWindows:
    print(so.OutputId, so.OutputUniqueId)
