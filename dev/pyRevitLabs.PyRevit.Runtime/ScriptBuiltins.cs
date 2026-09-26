using System.Collections.Generic;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// The builtin names pyRevit owns and injects into every script scope.
    /// </summary>
    /// <remarks>
    /// <b>Invariant:</b> every engine that injects
    /// <see cref="ScriptRuntimeConfigs.Variables"/> into a script scope must filter
    /// caller-supplied variables through <see cref="FilterUserVariables"/>. Scripts
    /// and the pyrevit library treat these names as guaranteed to hold what the
    /// runtime put there - <c>__revit__</c> above all, which the whole library
    /// resolves the host application through. Letting a command generator's
    /// variables win would break the host-handle contract silently, so the filter
    /// drops them rather than letting one engine accept what another rejects.
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
