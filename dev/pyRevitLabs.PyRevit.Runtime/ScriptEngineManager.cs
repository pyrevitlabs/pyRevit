using System;
using System.Collections.Generic;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class ScriptEngineManager {
        public static T GetEngine<T>(ref ScriptRuntime runtime) where T : ScriptEngine, new() {
            T engine = new T();
            engine.Init(ref runtime);

            if (engine.UseNewEngine) {
                SetCachedEngine<T>(engine.TypeId, engine);
            }
            else {
                var cachedEngine = GetCachedEngine<T>(engine.TypeId);
                if (cachedEngine != null) {
                    engine = cachedEngine;
                    engine.RecoveredFromCache = true;
                }
                else
                    SetCachedEngine<T>(engine.TypeId, engine);
            }
            return engine;
        }

        // dicts need to be flexible type since multiple signatures of the ScriptEngine
        // type could be placed inside this dictionary between pyRevit live reloads
        public static Dictionary<string, object> EngineDict {
            get {
                Dictionary<string, object> engineDict;
                var exstDict = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnginesDictKey);
                if (exstDict == null) {
                    engineDict = new Dictionary<string, object>();
                    AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnginesDictKey, engineDict);
                }
                else
                    engineDict = (Dictionary<string, object>)exstDict;
                return engineDict;
            }
        }

        // Engines that are mid-execution somewhere up the call stack, counted by
        // engine type id so nested executions unwind in order. Shutting one of
        // these down clears the builtins and disposes the output stream that the
        // suspended script resumes into, so they must survive a session reload
        // requested from inside a running command.
        public static Dictionary<string, int> ActiveEngineDict {
            get {
                Dictionary<string, int> activeDict;
                var exstDict = AppDomain.CurrentDomain.GetData(DomainStorageKeys.ActiveEnginesDictKey);
                if (exstDict == null) {
                    activeDict = new Dictionary<string, int>();
                    AppDomain.CurrentDomain.SetData(DomainStorageKeys.ActiveEnginesDictKey, activeDict);
                }
                else
                    activeDict = (Dictionary<string, int>)exstDict;
                return activeDict;
            }
        }

        public static bool IsEngineActive(string engineTypeId) {
            int depth;
            return engineTypeId != null
                && ActiveEngineDict.TryGetValue(engineTypeId, out depth)
                && depth > 0;
        }

        public static void EnterEngine(string engineTypeId) {
            if (engineTypeId == null)
                return;

            var activeDict = ActiveEngineDict;
            int depth;
            activeDict.TryGetValue(engineTypeId, out depth);
            activeDict[engineTypeId] = depth + 1;
        }

        public static void ExitEngine(string engineTypeId) {
            if (engineTypeId == null)
                return;

            var activeDict = ActiveEngineDict;
            int depth;
            if (!activeDict.TryGetValue(engineTypeId, out depth))
                return;

            if (depth > 1)
                activeDict[engineTypeId] = depth - 1;
            else
                activeDict.Remove(engineTypeId);
        }

        public static Dictionary<string, object> ClearEngines(string excludeEngine = null) {
            // shutdown all existing engines
            foreach (KeyValuePair<string, object> engineRecord in EngineDict) {
                if (engineRecord.Key == excludeEngine || IsEngineActive(engineRecord.Key))
                    continue;
                else
                    engineRecord.Value.GetType().GetMethod("Shutdown").Invoke(engineRecord.Value, new object[] { });
            }

            // create a new list
            var newEngineDict = new Dictionary<string, object>();
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnginesDictKey, newEngineDict);
            return newEngineDict;
        }

        private static T GetCachedEngine<T>(string engineTypeId) where T : ScriptEngine, new() {
            if (EngineDict.ContainsKey(engineTypeId)) {
                try {
                    return (T)EngineDict[engineTypeId];
                }
                catch (InvalidCastException) {
                    return null;
                }
            }
            return null;
        }

        private static void SetCachedEngine<T>(string engineTypeId, T engine) where T : ScriptEngine, new() {
            var cachedEngine = GetCachedEngine<T>(engine.TypeId);
            if (cachedEngine != null && !IsEngineActive(engine.TypeId))
                cachedEngine.Shutdown();
            EngineDict[engineTypeId] = engine;
        }
    }
}
