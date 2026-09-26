using System;
using System.Collections.Generic;
using System.Reflection;

using pyRevitLabs.NLog;

#if !NETFRAMEWORK
using System.Runtime.Loader;
#endif

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Owns the process-wide cache of live script engines, keyed by <see cref="ScriptEngine.TypeId"/>.
    /// </summary>
    /// <remarks>
    /// <para>
    /// The cache and the active-engine bookkeeping live in AppDomain data instead of in statics
    /// because every session load brings its own copy of this assembly. The dictionaries are
    /// <see cref="Dictionary{TKey,TValue}"/> from the shared framework, so every copy in the
    /// process reads and writes the same instances.
    /// </para>
    /// <para>
    /// Invariant: a cached engine is only handed to a caller that can cast it to the requested
    /// engine type, and an engine that is mid-execution is never shut down or dropped. A cached
    /// engine that can no longer be served - it belongs to a previous session load, or to a
    /// different copy of the runtime assembly - is shut down and dropped instead of silently
    /// overwritten, so engines don't pile up in the cache across session reloads. See
    /// <see cref="GetStaleReason"/>.
    /// </para>
    /// </remarks>
    public static class ScriptEngineManager {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static string _lastEvictedSessionId;

        /// <summary>
        /// Returns the cached engine for this command, or a new one when the cache cannot serve it.
        /// </summary>
        /// <remarks>
        /// A new engine is only cached when a later call can get it back: an engine that is
        /// mid-execution keeps its place in the cache, so a new engine created while one is
        /// running is handed to the caller but stays out of the cache. Callers only ever use
        /// the engine they are given.
        /// </remarks>
        public static T GetEngine<T>(ref ScriptRuntime runtime) where T : ScriptEngine, new() {
            T engine = new T();
            engine.Init(ref runtime);

            if (engine.UseNewEngine) {
                SetCachedEngine<T>(runtime.SessionUUID, engine);
            }
            else {
                var cachedEngine = GetCachedEngine<T>(runtime.SessionUUID, engine.TypeId);
                if (cachedEngine != null) {
                    engine = cachedEngine;
                    engine.RecoveredFromCache = true;
                }
                else
                    SetCachedEngine<T>(runtime.SessionUUID, engine);
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
        /// suspended script resumes into, so <see cref="ClearEngines"/>, cached-engine
        /// replacement and stale-engine eviction all skip active engines. This is what lets a
        /// running command request a session reload without crashing when it resumes.
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

        /// <summary>
        /// Shuts down every cached engine except <paramref name="excludeEngine"/> and engines that are
        /// mid-execution, then replaces the cache with one holding only the excluded engine.
        /// </summary>
        /// <param name="excludeEngine">
        /// Type id of the caller's own engine. The session preload script passes its shared session
        /// engine here, so it stays cached for the startup scripts and postload that resolve to the
        /// same type id.
        /// </param>
        /// <returns>The new engine cache.</returns>
        /// <remarks>
        /// Invariant: the excluded engine must remain in the returned cache. Dropping it makes every
        /// later caller with the same type id start a new engine and re-import its modules.
        /// </remarks>
        public static Dictionary<string, object> ClearEngines(string excludeEngine = null) {
            object excludedEngine = null;
            foreach (KeyValuePair<string, object> engineRecord in EngineDict) {
                if (engineRecord.Key == excludeEngine)
                    excludedEngine = engineRecord.Value;
                else if (!IsEngineActive(engineRecord.Key))
                    ShutdownEngine(engineRecord.Value);
            }

            var newEngineDict = new Dictionary<string, object>();
            if (excludedEngine != null)
                newEngineDict[excludeEngine] = excludedEngine;
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnginesDictKey, newEngineDict);
            return newEngineDict;
        }

        /// <summary>
        /// Identity of a cached engine - its type, the assembly that owns that type, the load
        /// context that assembly lives in, and whether it is mid-execution - for cache logs and
        /// for diagnosing a cache that stopped serving engines.
        /// </summary>
        /// <param name="engine">Cached engine, or null when nothing is cached.</param>
        /// <param name="engineTypeId">
        /// Key the engine is cached under, used to resolve its active state. Null when unknown.
        /// </param>
        internal static string DescribeEngine(object engine, string engineTypeId) {
            if (engine == null)
                return "no engine";

            Type engineType = engine.GetType();
            return string.Format(
                "{0} from {1}{2} (active: {3})",
                engineType.FullName,
                engineType.Assembly.FullName,
                DescribeLoadContext(engineType.Assembly),
                IsEngineActive(engineTypeId));
        }

        private static T GetCachedEngine<T>(string sessionId, string engineTypeId) where T : ScriptEngine, new() {
            EvictStaleEngines(sessionId);

            object cached;
            if (!EngineDict.TryGetValue(engineTypeId, out cached)) {
                LogCacheState(engineTypeId, typeof(T), null, "miss, nothing cached under this key");
                return null;
            }

            if (cached is T cachedEngine) {
                LogCacheState(engineTypeId, typeof(T), cachedEngine, "hit");
                return cachedEngine;
            }

            // The engine cached under this key is not one of ours: no engine created by this
            // copy of the runtime can ever be cast from it, so the key can never be served again.
            LogCacheState(engineTypeId, typeof(T), cached, "miss, cached engine has a stale type");
            EvictStaleEntry(engineTypeId, cached);
            return null;
        }

        private static void SetCachedEngine<T>(string sessionId, T engine) where T : ScriptEngine, new() {
            EvictStaleEngines(sessionId);

            object displaced;
            if (EngineDict.TryGetValue(engine.TypeId, out displaced)) {
                if (displaced is T) {
                    // A mid-execution engine keeps running to completion; it just stops being the
                    // one a later caller gets back.
                    if (IsEngineActive(engine.TypeId))
                        LogCacheState(engine.TypeId, typeof(T), displaced, "replaced by a new engine, replaced engine is still running");
                    else {
                        LogCacheState(engine.TypeId, typeof(T), displaced, "replaced by a new engine, shutting replaced engine down");
                        ShutdownEngine(displaced);
                    }
                }
                else if (!EvictStaleEntry(engine.TypeId, displaced)) {
                    return;
                }
            }

            EngineDict[engine.TypeId] = engine;
            LogCacheState(engine.TypeId, typeof(T), engine, "cached a new engine");
        }

        /// <summary>
        /// Shuts down and drops the engine cached under <paramref name="engineTypeId"/>, unless it
        /// is mid-execution.
        /// </summary>
        /// <returns>
        /// True when the key is now free for a new engine. False when the engine is still running
        /// and must keep its place in the cache.
        /// </returns>
        private static bool EvictStaleEntry(string engineTypeId, object cachedEngine) {
            if (IsEngineActive(engineTypeId)) {
                logger.Warn(
                    "Engine cache keeps the stale engine '{0}' until it finishes: {1}",
                    engineTypeId,
                    DescribeEngine(cachedEngine, engineTypeId));
                return false;
            }

            logger.Warn(
                "Engine cache drops the stale engine '{0}': {1}",
                engineTypeId,
                DescribeEngine(cachedEngine, engineTypeId));
            ShutdownEngine(cachedEngine);
            EngineDict.Remove(engineTypeId);
            return true;
        }

        /// <summary>
        /// Drops every cached engine that the given session can never receive, once per session.
        /// </summary>
        /// <remarks>
        /// A session load seeds a new session uuid, so the engines a previous load left behind are
        /// keyed under ids no later caller can produce. Nothing else would ever look at them again,
        /// and each one keeps a whole interpreter (with its imported modules) alive for the rest of
        /// the Revit session, which is what turns repeated reloads into a multi-gigabyte heap.
        /// </remarks>
        private static void EvictStaleEngines(string sessionId) {
            if (string.IsNullOrEmpty(sessionId) || sessionId == _lastEvictedSessionId)
                return;

            _lastEvictedSessionId = sessionId;

            var staleEntries = new List<KeyValuePair<string, string>>();
            foreach (KeyValuePair<string, object> engineRecord in EngineDict) {
                string reason = GetStaleReason(sessionId, engineRecord.Key, engineRecord.Value);
                if (reason != null && !IsEngineActive(engineRecord.Key))
                    staleEntries.Add(new KeyValuePair<string, string>(engineRecord.Key, reason));
            }

            foreach (KeyValuePair<string, string> staleEntry in staleEntries) {
                object staleEngine = EngineDict[staleEntry.Key];
                logger.Debug(
                    "Engine cache drops '{0}' ({1}): {2}",
                    staleEntry.Key,
                    staleEntry.Value,
                    DescribeEngine(staleEngine, staleEntry.Key));
                ShutdownEngine(staleEngine);
                EngineDict.Remove(staleEntry.Key);
            }
        }

        /// <summary>
        /// Why a cached engine is dead weight for the given session, or null while the engine is
        /// still the one this session would cache under that key.
        /// </summary>
        private static string GetStaleReason(string sessionId, string engineTypeId, object cachedEngine) {
            if (!engineTypeId.StartsWith(sessionId + ":", StringComparison.Ordinal))
                return "cached by a previous session load";

            if (cachedEngine == null)
                return null;

            // A second copy of the runtime assembly in the process (a new load context, or the
            // same assembly loaded twice) brings its own ScriptEngine type, so nothing created by
            // this copy can ever be cast from that engine.
            if (!(cachedEngine is ScriptEngine))
                return "created by a different copy of the runtime assembly";

            return null;
        }

        /// <summary>
        /// Shuts an engine down through its own type, which is the only way to reach an engine
        /// whose type this copy of the runtime cannot cast to.
        /// </summary>
        private static void ShutdownEngine(object engine) {
            if (engine == null)
                return;

            MethodInfo shutdown = engine.GetType().GetMethod("Shutdown", BindingFlags.Instance | BindingFlags.Public);
            if (shutdown == null) {
                logger.Warn("Cannot shut down {0}: it has no public Shutdown()", DescribeEngine(engine, null));
                return;
            }

            try {
                shutdown.Invoke(engine, null);
            }
            catch (Exception ex) {
                logger.Warn(ex, "Shutdown of {0} failed", DescribeEngine(engine, null));
            }
        }

        private static void LogCacheState(string engineTypeId, Type requestedEngineType, object cachedEngine, string outcome) {
            if (!logger.IsDebugEnabled)
                return;

            logger.Debug(
                "Engine cache {0} for '{1}': asked for {2}, holds {3}",
                outcome,
                engineTypeId,
                requestedEngineType.Name,
                DescribeEngine(cachedEngine, engineTypeId));
        }

        private static string DescribeLoadContext(Assembly assembly) {
#if !NETFRAMEWORK
            AssemblyLoadContext context = AssemblyLoadContext.GetLoadContext(assembly);
            return context == null
                ? string.Empty
                : string.Format(" loaded into load context '{0}'", context.Name);
#else
            return string.Empty;
#endif
        }
    }
}
