using System;
using System.Linq;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Tells an agent which Python its scripts run on: the default engine, the exact
    /// language version of each available engine, and the syntax each one rejects.
    /// </summary>
    /// <remarks>
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

        public static JObject Describe(EnvDictionary env) {
            var defaultEngine = PyRevitConfigs.GetAgentEngine();
            var ironPython = DescribeIronPython(env.PyRevitIPYVersion);
            var cpython = DescribeCPython(env.PyRevitCPYVersion);
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
        internal static string FormatIronPythonVersion(string code) {
            if (string.IsNullOrEmpty(code) || !code.All(char.IsDigit) || code.Length < 3)
                return code;
            return code[0] + "." + code[1] + "." + code.Substring(2);
        }

        internal static string FormatCPythonVersion(string code) {
            if (string.IsNullOrEmpty(code) || !code.All(char.IsDigit) || code.Length < 4)
                return code;
            return code[0] + "." + code.Substring(1, 2) + "." + code.Substring(3);
        }

        private static JObject DescribeIronPython(string code) {
            var version = FormatIronPythonVersion(code);
            var isPython2 = version != null && version.StartsWith("2.", StringComparison.Ordinal);
            return new JObject {
                ["available"] = !string.IsNullOrEmpty(code),
                ["implementation"] = "IronPython",
                ["python"] = version,
                ["syntax"] = isPython2 ? IronPython2Syntax : IronPython3Syntax,
            };
        }

        private static JObject DescribeCPython(string code) {
            return new JObject {
                ["available"] = !string.IsNullOrEmpty(code),
                ["implementation"] = "CPython",
                ["python"] = FormatCPythonVersion(code),
                ["syntax"] = CPythonSyntax,
            };
        }
    }
}
