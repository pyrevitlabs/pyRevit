using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;

using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

using Console = Colorful.Console;

namespace pyRevitCLI {
    internal enum McpClientKind {
        Claude,
        Codex,
        Cursor,
        VSCode,
        OpenCode,
    }

    /// <summary>
    /// <c>pyrevit agent</c>, <c>pyrevit configs agent</c> and <c>pyrevit mcp install|uninstall</c>.
    /// </summary>
    internal static class PyRevitCLIAgentCmds {
        public const string McpServerName = "pyrevit";

        public static void PrintStatus(bool json) {
            var instances = PyRevitAgentClient.GetInstances();
            if (json) {
                Console.WriteLine(new JArray(instances.Select(instance => instance.ToJson())).ToString(Formatting.Indented));
                return;
            }

            Console.WriteLine(string.Format("Agent host: {0} (policy: {1}, default engine: {2}, user skills: {3})",
                PyRevitConfigs.GetAgentEnabled() ? "enabled" : "disabled",
                PyRevitConfigs.GetAgentPolicy(),
                PyRevitConfigs.GetAgentEngine(),
                PyRevitConfigs.GetAgentUserSkillsEnabled() ? "enabled" : "disabled"));

            if (instances.Count == 0) {
                Console.WriteLine("No running Revit with the agent host.");
                return;
            }

            foreach (var instance in instances) {
                string state;
                try {
                    PyRevitAgentClient.Call(instance, "ping");
                    state = "responding";
                }
                catch (AgentClientException ex) {
                    state = "not responding (" + ex.Code + ")";
                }
                Console.WriteLine(string.Format("Revit {0} (build {1}) pid {2}: {3}",
                    instance.RevitVersion, instance.RevitBuild, instance.ProcessId, state));
            }
        }

        public static void PrintContext(string revitSelector) {
            var instance = PyRevitAgentClient.Resolve(revitSelector);
            Console.WriteLine(PyRevitAgentClient.Call(instance, "get_context").ToString(Formatting.Indented));
        }

        public static void RunScript(string scriptFile, string mode, string engine, string title, string inputsJson, string revitSelector, string timeoutSeconds = null, string workspace = null) {
            if (!File.Exists(scriptFile))
                throw new PyRevitException("Script file not found: " + scriptFile);
            if (timeoutSeconds != null && !double.TryParse(timeoutSeconds, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out _))
                throw new PyRevitException("--timeout must be a number of seconds: " + timeoutSeconds);

            var parameters = new JObject {
                ["script"] = File.ReadAllText(scriptFile),
                ["mode"] = mode ?? "query",
                ["title"] = title ?? Path.GetFileName(scriptFile),
                ["inputs"] = string.IsNullOrWhiteSpace(inputsJson) ? new JObject() : JToken.Parse(inputsJson),
            };
            if (engine != null)
                parameters["engine"] = engine;
            if (timeoutSeconds != null)
                parameters["timeout_s"] = double.Parse(timeoutSeconds, System.Globalization.CultureInfo.InvariantCulture);
            if (workspace != null)
                parameters["workspace"] = Path.GetFullPath(workspace);

            var instance = PyRevitAgentClient.Resolve(revitSelector);
            var response = PyRevitAgentClient.Call(instance, "run", parameters);
            Console.WriteLine(response.ToString(Formatting.Indented));

            var status = response.Value<string>("status");
            if (status != "ok")
                Environment.ExitCode = 1;
        }

        public static void PrintRuns(string limit) {
            var count = int.TryParse(limit, out var parsed) && parsed > 0 ? parsed : 20;
            var runDirs = PyRevitAgentClient.GetRecentRunDirs(count);
            if (runDirs.Count == 0) {
                Console.WriteLine("No agent runs recorded.");
                return;
            }

            foreach (var runDir in runDirs) {
                var response = TryReadJson(Path.Combine(runDir, "response.json"));
                var request = TryReadJson(Path.Combine(runDir, "request.json"));
                var name = Path.GetFileName(runDir);
                var runId = name.Substring(name.LastIndexOf('-') + 1);
                Console.WriteLine(string.Format("{0}  {1,-8} {2,-10} {3,-12} {4}",
                    runId,
                    request?.Value<string>("mode") ?? "?",
                    response?.Value<string>("status") ?? "no-result",
                    response?.Value<string>("decision") ?? string.Empty,
                    request?.Value<string>("title") ?? string.Empty));
            }
        }

        public static void ShowRun(string runId) {
            var runDir = PyRevitAgentClient.FindRunDir(runId)
                ?? throw new PyRevitException("No recorded agent run with id " + runId);
            Console.WriteLine("Run folder: " + runDir);
            foreach (var file in new[] { "request.json", "script.py", "response.json" }) {
                var path = Path.Combine(runDir, file);
                if (!File.Exists(path))
                    continue;
                Console.WriteLine();
                Console.WriteLine("--- " + file);
                Console.WriteLine(File.ReadAllText(path));
            }
        }

        public static void ConfigureEnabled(bool? enable) {
            if (enable.HasValue) {
                PyRevitConfigs.SetAgentEnabled(enable.Value);
                Console.WriteLine("Agent host {0}. Reload pyRevit or restart Revit to apply.",
                    enable.Value ? "enabled" : "disabled");
            }
            else
                Console.WriteLine("Agent host is {0}", PyRevitConfigs.GetAgentEnabled() ? "Enabled" : "Disabled");
        }

        public static void ConfigurePolicy(string policy) {
            if (policy != null)
                PyRevitConfigs.SetAgentPolicy(policy);
            else
                Console.WriteLine("Agent policy: " + PyRevitConfigs.GetAgentPolicy());
        }

        public static void ConfigureEngine(string engine) {
            if (engine != null)
                PyRevitConfigs.SetAgentEngine(engine);
            else
                Console.WriteLine("Agent default engine: " + PyRevitConfigs.GetAgentEngine());
        }

        public static void ConfigureUserSkills(bool? enable) {
            if (enable.HasValue) {
                PyRevitConfigs.SetAgentUserSkillsEnabled(enable.Value);
                Console.WriteLine("Agent user skills {0}.", enable.Value ? "enabled" : "disabled");
            }
            else
                Console.WriteLine("Agent user skills are {0}", PyRevitConfigs.GetAgentUserSkillsEnabled() ? "Enabled" : "Disabled");
        }

        /// <summary>
        /// Registers <c>pyrevit mcp</c> with an MCP client.
        /// </summary>
        /// <remarks>
        /// Registers the path of the <c>pyrevit.exe</c> that runs this command, so run it from
        /// the clone the client should use. Claude Code and Codex are configured through their
        /// own CLIs; Cursor and VS Code through their <c>mcp.json</c> files, updated in place so
        /// other servers in those files are kept.
        /// </remarks>
        public static void InstallMcp(McpClientKind client, bool project) {
            var command = Environment.ProcessPath;
            McpClient.For(client).Install(command, project);

            Console.WriteLine($"Registered MCP server \"{McpServerName}\" ({command} mcp) with {client}.");
            if (PyRevitConfigs.GetAgentEnabled())
                Console.WriteLine("Agent host remains enabled. Reload pyRevit or restart Revit, then restart the MCP client.");
            else
                Console.WriteLine("Enable the agent host with 'pyrevit configs agent enable', reload pyRevit or restart Revit, then restart the MCP client.");
        }

        public static void UninstallMcp(McpClientKind client, bool project) {
            McpClient.For(client).Uninstall(project);
        }

        /// <summary>
        /// Removes the pyrevit MCP server from every client's user-level configuration, for the
        /// uninstaller. Never throws: a client that isn't installed, has no entry, or has a
        /// config that can't be rewritten is skipped with a message.
        /// </summary>
        /// <param name="ownedOnly">
        /// Keeps a registration whose command is not this <c>pyrevit.exe</c>, or whose command
        /// can't be read, so uninstalling one installation leaves another one's registration.
        /// </param>
        /// <remarks>
        /// Only the running account's own configs are touched, elevated or not. An elevated
        /// process must not rewrite files in another user's profile: that user controls the path
        /// and can redirect the write elsewhere with a junction or symlink.
        /// </remarks>
        public static void UninstallMcpFromAllClients(bool ownedOnly) {
            UninstallMcpFromAllClients(
                ownedOnly,
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData));
        }

        /// <summary>
        /// Same as <see cref="UninstallMcpFromAllClients(bool)"/> for the profile folders given,
        /// so a test can run it against a temporary profile.
        /// </summary>
        /// <remarks>
        /// Without <paramref name="ownedOnly"/> the user-level configs are those of the running
        /// account, whatever folders are passed.
        /// </remarks>
        internal static void UninstallMcpFromAllClients(bool ownedOnly, string home, string appData) {
            foreach (var client in McpClient.All) {
                try {
                    client.UninstallFromUserProfile(ownedOnly, home, appData);
                }
                catch (Exception ex) {
                    Console.WriteLine($"Skipped {client.Kind}: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Starts a client's own CLI. Replaced by tests so they never run the real <c>claude</c>
        /// or <c>codex</c> against the developer's profile.
        /// </summary>
        internal static Action<string, string, bool> ClientCli = RunClientCliProcess;

        /// <summary>
        /// Runs a client's own CLI (<c>claude</c>, <c>codex</c>) by full path.
        /// </summary>
        /// <remarks>
        /// This command is often launched from Revit (Settings → Agent Runtime), and Revit's
        /// environment keeps the PATH from when Revit started, which misses tools installed since.
        /// So the tool is located on the PATH freshly read from the registry plus the usual install
        /// folders, and the child process gets that fresh PATH too.
        /// </remarks>
        private static void RunClientCliProcess(string tool, string arguments, bool ignoreFailure) {
            var executable = ResolveClientTool(tool);
            if (executable == null) {
                if (ignoreFailure)
                    return;
                throw new PyRevitException(
                    $"Could not find the '{tool}' command on PATH or in its usual install folders. "
                    + $"Install it or add its folder to PATH, then retry. To register by hand, run: {tool} {arguments}");
            }

            var startInfo = new ProcessStartInfo("cmd.exe", $"/d /s /c \"\"{executable}\" {arguments}\"") {
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };
            startInfo.Environment["PATH"] = FreshPath();

            Process process;
            try {
                process = Process.Start(startInfo);
            }
            catch (Exception ex) {
                throw new PyRevitException($"Could not run '{tool}': {ex.Message}");
            }

            using (process) {
                var output = process.StandardOutput.ReadToEnd();
                var error = process.StandardError.ReadToEnd();
                process.WaitForExit();
                if (ignoreFailure)
                    return;
                if (!string.IsNullOrWhiteSpace(output))
                    Console.WriteLine(output.Trim());
                if (process.ExitCode != 0)
                    throw new PyRevitException(
                        $"'{tool} {arguments}' failed (exit code {process.ExitCode}). "
                        + (string.IsNullOrWhiteSpace(error) ? $"Is {tool} installed and on PATH?" : error.Trim()));
            }
        }

        private static string ResolveClientTool(string tool) {
            foreach (var directory in ToolSearchDirectories())
                foreach (var extension in new[] { ".exe", ".cmd", ".bat" }) {
                    var candidate = Path.Combine(directory, tool + extension);
                    if (File.Exists(candidate))
                        return candidate;
                }
            return null;
        }

        private static IEnumerable<string> ToolSearchDirectories() {
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var knownInstallFolders = new[] {
                Path.Combine(home, ".local", "bin"),
                Path.Combine(appData, "npm"),
                Path.Combine(home, "scoop", "shims"),
            };
            return FreshPath().Split(Path.PathSeparator)
                .Concat(knownInstallFolders)
                .Where(directory => !string.IsNullOrWhiteSpace(directory))
                .Distinct(StringComparer.OrdinalIgnoreCase);
        }

        private static string FreshPath() {
            var entries = new[] {
                    Environment.GetEnvironmentVariable("PATH"),
                    Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Machine),
                    Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.User),
                }
                .Where(value => !string.IsNullOrEmpty(value))
                .SelectMany(value => value.Split(Path.PathSeparator))
                .Select(entry => Environment.ExpandEnvironmentVariables(entry.Trim()))
                .Where(entry => entry.Length > 0)
                .Distinct(StringComparer.OrdinalIgnoreCase);
            return string.Join(Path.PathSeparator.ToString(), entries);
        }

        internal static JObject TryReadJson(string path) {
            try {
                return File.Exists(path) ? JObject.Parse(File.ReadAllText(path)) : null;
            }
            catch (Exception) {
                return null;
            }
        }
    }
}
