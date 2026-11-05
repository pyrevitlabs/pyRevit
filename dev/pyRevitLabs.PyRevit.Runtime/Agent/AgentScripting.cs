using System;
using System.IO;
using System.Linq;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Tells an agent which Python its scripts run on: the default engine, the exact
    /// language version of each available engine, and the syntax each one rejects.
    /// </summary>
    /// <remarks>
    /// Invariant: an engine is reported <c>available</c> only when a run on it can start.
    /// CPython resolves its DLL from the same clone <c>CPythonEngine</c> uses (the attached
    /// clone, else the running one), so it is unavailable only when that clone has no engine
    /// DLL, and <c>unavailable_reason</c> says why. A run on an unavailable engine fails with
    /// <c>engine_unavailable</c> before any code runs.
    /// Version values from the session env are not trusted blindly: an unattached session
    /// seeds <c>0</c> or <c>Unknown</c>, which are reported as null, never as a version.
    /// The syntax limits of IronPython 3.4 were measured in Revit on 3.4.2, not taken from
    /// the language level: it accepts f-strings, variable annotations and <c>*</c>/<c>**</c>
    /// unpacking in literals, but rejects the walrus operator, async/await, underscores in
    /// numeric literals and positional-only parameters. Re-check them when the engine is upgraded.
    /// </remarks>
    internal static class AgentScripting {
        private const string IronPython2Syntax =
            "Python 2.7 syntax. Not available: f-strings, type annotations, keyword-only arguments, "
            + "*/** unpacking inside list/dict literals, nonlocal, async/await, walrus (:=). "
            + "Use '%' formatting or str.format; print(x) with a single argument works.";

        private const string IronPython3Syntax =
            "Python 3.4 syntax plus f-strings, variable annotations and */** unpacking in literals. "
            + "Not available: walrus (:=), async/await, underscores in numbers (1_000), "
            + "positional-only parameters (/), match statements.";

        private const string CPythonSyntax =
            "Full CPython syntax for this version. The Revit API is reached through pythonnet, "
            + "and pyrevitlib features built for IronPython (such as pyrevit.forms) may be limited.";

        public static JObject Describe(EnvDictionary env, string revitVersion) {
            var defaultEngine = PyRevitConfigs.GetAgentEngine();
            var ironPython = DescribeIronPython(env.PyRevitIPYVersion);
            var cpython = DescribeCPython(env.PyRevitCPYVersion, revitVersion);
            var chosen = defaultEngine == PyRevitConsts.ConfigsAgentEngineCPython ? cpython : ironPython;

            return new JObject {
                ["default_engine"] = defaultEngine,
                ["default_python"] = chosen["python"],
                ["default_syntax"] = chosen["syntax"],
                ["engines"] = new JObject {
                    [PyRevitConsts.ConfigsAgentEngineIronPython] = ironPython,
                    [PyRevitConsts.ConfigsAgentEngineCPython] = cpython,
                },
                ["how_to_choose"] = "Scripts run on default_engine unless a run passes engine='ironpython' or "
                    + "engine='cpython'. Write code for that engine's python version and syntax. Every run "
                    + "response reports the engine and the exact Python version that executed it.",
            };
        }

        /// <summary>
        /// Formats pyRevit's compact engine codes: IronPython <c>2712</c> → <c>2.7.12</c>,
        /// <c>342</c> → <c>3.4.2</c>; CPython <c>3123</c> → <c>3.12.3</c>.
        /// </summary>
        /// <remarks>
        /// Also accepts a dotted assembly version (<c>2.7.12.0</c> to <c>2.7.12</c>). Returns null
        /// for anything else, including the <c>0</c> and <c>Unknown</c> of an unattached session.
        /// </remarks>
        internal static string FormatIronPythonVersion(string code) {
            if (TryFormatDotted(code, out var dotted))
                return dotted;
            if (!IsVersionCode(code, 3))
                return null;
            return code[0] + "." + code[1] + "." + code.Substring(2);
        }

        internal static string FormatCPythonVersion(string code) {
            if (TryFormatDotted(code, out var dotted))
                return dotted;
            if (!IsVersionCode(code, 4))
                return null;
            return code[0] + "." + code.Substring(1, 2) + "." + code.Substring(3);
        }

        /// <summary>
        /// Throws <c>engine_unavailable</c> when a run asks for an engine that can't start, so
        /// the agent gets the reason instead of a host error from inside the engine.
        /// </summary>
        public static void EnsureAvailable(AgentEngine engine, string revitVersion) {
            if (engine != AgentEngine.CPython)
                return;
            var env = new EnvDictionary();
            if (!TryResolveCPython(env.PyRevitCPYVersion, revitVersion, out var reason))
                throw new AgentException("engine_unavailable",
                    "The CPython engine can't run in this session: " + reason + " Use engine 'ironpython'.");
        }

        private static bool IsVersionCode(string code, int minLength) {
            return !string.IsNullOrEmpty(code) && code.Length >= minLength && code.All(char.IsDigit) && code.Any(c => c != '0');
        }

        private static bool TryFormatDotted(string code, out string dotted) {
            dotted = null;
            if (string.IsNullOrEmpty(code) || !code.Contains(".") || !Version.TryParse(code, out var version))
                return false;
            dotted = version.Build >= 0
                ? $"{version.Major}.{version.Minor}.{version.Build}"
                : $"{version.Major}.{version.Minor}";
            return true;
        }

        private static JObject DescribeIronPython(string code) {
            var version = FormatIronPythonVersion(code);
            var isPython2 = version != null && version.StartsWith("2.", StringComparison.Ordinal);
            return new JObject {
                ["available"] = true,
                ["implementation"] = "IronPython",
                ["python"] = version,
                ["syntax"] = version == null
                    ? "Unknown IronPython version; every run response reports the version that ran. " + IronPython2Syntax
                    : isPython2 ? IronPython2Syntax : IronPython3Syntax,
            };
        }

        private static JObject DescribeCPython(string code, string revitVersion) {
            var available = TryResolveCPython(code, revitVersion, out var reason);
            var description = new JObject {
                ["available"] = available,
                ["implementation"] = "CPython",
                ["python"] = FormatCPythonVersion(code),
                ["syntax"] = CPythonSyntax,
            };
            if (!available)
                description["unavailable_reason"] = reason;
            return description;
        }

        private static bool TryResolveCPython(string code, string revitVersion, out string reason) {
            reason = null;
            if (!IsVersionCode(code, 4)) {
                reason = "no CPython engine is installed with this pyRevit.";
                return false;
            }
            if (!int.TryParse(revitVersion, out var revitYear)) {
                reason = "the Revit version is unknown.";
                return false;
            }
            try {
                var clonePath = CPythonEngine.ResolveEngineClonePath(revitYear);
                if (clonePath == null) {
                    reason = $"pyRevit is not attached to Revit {revitYear} (run 'pyrevit attach') and the running clone could not be found.";
                    return false;
                }
                var engine = PyRevitClone.GetCPythonEngine(clonePath, new PyRevitEngineVersion(int.Parse(code)));
                if (engine == null || !File.Exists(engine.AssemblyPath)) {
                    reason = $"the CPython {FormatCPythonVersion(code)} engine DLL is missing from '{clonePath}'.";
                    return false;
                }
                return true;
            }
            catch (Exception ex) {
                reason = "its engine could not be resolved: " + ex.Message;
                return false;
            }
        }
    }
}
