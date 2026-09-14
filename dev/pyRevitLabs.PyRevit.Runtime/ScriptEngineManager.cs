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

        /// <summary>
        /// Engines that are mid-execution somewhere up the call stack, keyed by engine type id,
        /// with the number of executions of each that are currently in progress.
        /// </summary>
        /// <remarks>
        /// <para>
        /// Shutting down an active engine clears the builtins and disposes the output stream the
        /// suspended script resumes into, so <see cref="ClearEngines"/> and cached-engine
        /// replacement skip active engines. This is what lets a running command request a session
        /// reload without crashing when it resumes.
        /// </para>
        /// <para>
        /// Invariant: only touched from the Revit main thread, so the dictionary is not
        /// synchronized. <see cref="ScriptExecutor.ExecuteScript"/> guarantees this by sending
        /// off-thread callers through its ExternalEvent, and
        /// <see cref="ScriptExecutor.ExecuteScriptInApiContext"/> is only called from Revit API
        /// callbacks. Any change that runs scripts off the main thread must add synchronization
        /// here, locking on the dictionary instance itself: it lives in AppDomain data and is
        /// shared by every Runtime assembly loaded across reloads.
        /// </para>
        /// </remarks>
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

        /// <summary>
        /// Whether an execution of the engine is still in progress, meaning it must not be shut
        /// down. See <see cref="ActiveEngineDict"/>.
        /// </summary>
        public static bool IsEngineActive(string engineTypeId) {
            int depth;
            return engineTypeId != null
                && ActiveEngineDict.TryGetValue(engineTypeId, out depth)
                && depth > 0;
        }

        /// <summary>
        /// Marks one execution of the engine as in progress, protecting the engine from shutdown
        /// until the matching <see cref="ExitEngine"/>. Calls may nest.
        /// </summary>
        /// <remarks>
        /// Invariant: every call must be paired with <see cref="ExitEngine"/> in a <c>finally</c>
        /// block. A missed exit leaves the engine marked active for the rest of the process, so it
        /// is never shut down or replaced.
        /// </remarks>
        public static void EnterEngine(string engineTypeId) {
            if (engineTypeId == null)
                return;

            var activeDict = ActiveEngineDict;
            int depth;
            activeDict.TryGetValue(engineTypeId, out depth);
            activeDict[engineTypeId] = depth + 1;
        }

        /// <summary>
        /// Releases one <see cref="EnterEngine"/> mark. The engine can be shut down again once no
        /// executions remain. An exit with no matching enter is ignored.
        /// </summary>
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
