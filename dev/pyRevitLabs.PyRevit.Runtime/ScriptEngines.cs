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
            TypeId = BuildTypeId(runtime.SessionUUID, runtime.EngineType, extensionScope);

            // default to false since this is a new engine
            RecoveredFromCache = false;
        }

        /// <summary>
        /// The <see cref="TypeId"/> an engine of this type and scope gets in the given session,
        /// for callers that look the engine up in <see cref="ScriptEngineManager.EngineDict"/>.
        /// </summary>
        public static string BuildTypeId(string sessionId, ScriptEngineType engineType, string extensionScope) {
            return string.Join(":", sessionId, engineType.ToString(), extensionScope);
        }

        public virtual void Start(ref ScriptRuntime runtime) { }
        public virtual int Execute(ref ScriptRuntime runtime) { return ScriptExecutorResultCodes.Succeeded; }
        public virtual void Stop(ref ScriptRuntime runtime) { }
        public virtual void Shutdown() { }
    }
}
