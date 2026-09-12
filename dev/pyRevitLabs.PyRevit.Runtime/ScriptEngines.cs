using System.Collections.Generic;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public enum ScriptEngineType {
        Unknown,
        IronPython,
        CPython,
        CSharp,
        Invoke,
        VisualBasic,
        IronRuby,
        DynamoBIM,
        Grasshopper,
        Content,
        HyperLink
    }

    public class ScriptEngineConfigs {
    }

    public class ScriptEngine {
        /// <summary>
        /// Builtin names pyRevit owns; caller-supplied
        /// <see cref="ScriptRuntimeConfigs.Variables"/> may never overwrite them.
        /// </summary>
        /// <remarks>
        /// Invariant: every engine that injects <see cref="ScriptRuntimeConfigs.Variables"/>
        /// into a script scope must filter through this set. Scripts and the pyrevit
        /// library treat these names as guaranteed to hold what the runtime put there -
        /// <c>__revit__</c> above all, which the whole library resolves the host
        /// application through.
        /// </remarks>
        public static readonly HashSet<string> ReservedBuiltinNames = new HashSet<string> {
            "__execid__",
            "__timestamp__",
            "__cachedengine__",
            "__cachedengineid__",
            "__scriptruntime__",
            "__revit__",
            "__commanddata__",
            "__elements__",
            "__uibutton__",
            "__commandpath__",
            "__configcommandpath__",
            "__commandname__",
            "__commandbundle__",
            "__commandextension__",
            "__commanduniqueid__",
            "__commandcontrolid__",
            "__forceddebugmode__",
            "__shiftclick__",
            "__result__",
            "__eventsender__",
            "__eventargs__"
        };

        public string Id { get; private set; }

        /// <summary>
        /// Unique cache key for this engine: session id, engine type, and command extension -
        /// unless the caller opted into <see cref="ScriptRuntimeConfigs.SharedSessionEngine"/>, in
        /// which case the extension is dropped from the key so every opted-in caller within the
        /// same session load resolves to the same cached engine.
        /// </summary>
        public string TypeId { get; private set; }

        public virtual bool UseNewEngine { get; set; }
        public virtual bool RecoveredFromCache { get; set; }

        public virtual void Init(ref ScriptRuntime runtime) {
            Id = CommonUtils.NewShortUUID();
            // unqiue typeid of the engine
            // based on session_id, engine type, and command extension
            var extensionScope = runtime.ScriptRuntimeConfigs.SharedSessionEngine
                ? "__pyrevit_session__"
                : runtime.ScriptData.CommandExtension;
            TypeId = string.Join(":",
                runtime.SessionUUID,
                runtime.EngineType.ToString(),
                extensionScope);

            // default to false since this is a new engine
            RecoveredFromCache = false;
        }

        public virtual void Start(ref ScriptRuntime runtime) { }
        public virtual int Execute(ref ScriptRuntime runtime) { return ScriptExecutorResultCodes.Succeeded; }
        public virtual void Stop(ref ScriptRuntime runtime) { }
        public virtual void Shutdown() { }
    }
}
