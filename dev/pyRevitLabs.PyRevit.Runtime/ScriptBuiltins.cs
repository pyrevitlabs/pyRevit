using System.Collections.Generic;
using System.IO;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// The runtime variables pyRevit owns and injects into every script scope.
    /// </summary>
    /// <remarks>
    /// <b>Invariant:</b> every engine that injects
    /// <see cref="ScriptRuntimeConfigs.Variables"/> into a script scope must filter
    /// caller-supplied variables through <see cref="FilterUserVariables"/>. These
    /// runtime values are available both as engine builtins and in the individual
    /// execution scope so deferred callbacks retain the identity of their command.
    /// </remarks>
    internal static class ScriptBuiltins {
        private static readonly HashSet<string> ReservedNames = new HashSet<string> {
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
            "__eventargs__",
        };

        internal static IDictionary<string, object> CreateRuntimeVariables(
            ScriptRuntime runtime,
            bool recoveredFromCache,
            string typeId) {
            var scriptData = runtime.ScriptData;
            var runtimeConfigs = runtime.ScriptRuntimeConfigs;

            return new Dictionary<string, object> {
                { "__execid__", runtime.ExecId },
                { "__timestamp__", runtime.ExecTimestamp },
                { "__cachedengine__", recoveredFromCache },
                { "__cachedengineid__", typeId },
                { "__scriptruntime__", runtime },
                { "__revit__", runtime.UIApp },
                { "__commanddata__", runtimeConfigs.CommandData },
                { "__elements__", runtimeConfigs.SelectedElements },
                { "__uibutton__", runtime.UIControl },
                { "__commandpath__", Path.GetDirectoryName(scriptData.ScriptPath) },
                { "__configcommandpath__", Path.GetDirectoryName(scriptData.ConfigScriptPath) },
                { "__commandname__", scriptData.CommandName },
                { "__commandbundle__", scriptData.CommandBundle },
                { "__commandextension__", scriptData.CommandExtension },
                { "__commanduniqueid__", scriptData.CommandUniqueId },
                { "__commandcontrolid__", scriptData.CommandControlId },
                { "__forceddebugmode__", runtimeConfigs.DebugMode },
                { "__shiftclick__", runtimeConfigs.ConfigMode },
                { "__result__", runtime.GetResultsDictionary() },
                { "__eventsender__", runtimeConfigs.EventSender },
                { "__eventargs__", runtimeConfigs.EventArgs },
            };
        }

        /// <summary>
        /// Whether <paramref name="name"/> is a builtin pyRevit reserves for itself.
        /// </summary>
        internal static bool IsReserved(string name) {
            return ReservedNames.Contains(name);
        }

        /// <summary>
        /// The subset of <paramref name="variables"/> that may be injected as-is,
        /// i.e. everything that does not collide with a reserved builtin.
        /// </summary>
        internal static IEnumerable<KeyValuePair<string, object>> FilterUserVariables(
            IDictionary<string, object> variables) {
            if (variables == null)
                yield break;

            foreach (var variable in variables) {
                if (IsReserved(variable.Key))
                    continue;
                yield return variable;
            }
        }
    }
}
