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
        public string TypeId { get; private set; }

        public virtual bool UseNewEngine { get; set; }
        public virtual bool RecoveredFromCache { get; set; }

        public virtual void Init(ref ScriptRuntime runtime) {
            Id = CommonUtils.NewShortUUID();
            // unqiue typeid of the engine
            // based on session_id, engine type, and command extension
            TypeId = string.Join(":",
                runtime.SessionUUID,
                runtime.EngineType.ToString(),
                runtime.ScriptData.CommandExtension);

            // default to false since this is a new engine
            RecoveredFromCache = false;
        }

        public virtual void Start(ref ScriptRuntime runtime) { }
        public virtual int Execute(ref ScriptRuntime runtime) { return ScriptExecutorResultCodes.Succeeded; }
        public virtual void Stop(ref ScriptRuntime runtime) { }
        public virtual void Shutdown() { }
    }
}
