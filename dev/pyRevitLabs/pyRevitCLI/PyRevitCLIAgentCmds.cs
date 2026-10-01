using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

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
        private static readonly Encoding Utf8 = new UTF8Encoding(false);

        public static void PrintStatus(bool json) {
            var instances = PyRevitAgentClient.GetInstances();
            if (json) {
                Console.WriteLine(new JArray(instances.Select(instance => instance.ToJson())).ToString(Formatting.Indented));
                return;
            }

            Console.WriteLine(string.Format("Agent host: {0} (policy: {1}, default engine: {2})",
                PyRevitConfigs.GetAgentEnabled() ? "enabled" : "disabled",
                PyRevitConfigs.GetAgentPolicy(),
                PyRevitConfigs.GetAgentEngine()));

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

        public static void RunScript(string scriptFile, string mode, string engine, string title, string inputsJson, string revitSelector) {
            if (!File.Exists(scriptFile))
                throw new PyRevitException("Script file not found: " + scriptFile);

            var parameters = new JObject {
                ["script"] = File.ReadAllText(scriptFile),
                ["mode"] = mode ?? "query",
                ["title"] = title ?? Path.GetFileName(scriptFile),
                ["inputs"] = string.IsNullOrWhiteSpace(inputsJson) ? new JObject() : JToken.Parse(inputsJson),
            };
            if (engine != null)
                parameters["engine"] = engine;

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
            switch (client) {
                case McpClientKind.Claude:
                    var scope = project ? "project" : "user";
                    RunClientCli("claude", $"mcp remove --scope {scope} {McpServerName}", ignoreFailure: true);
                    RunClientCli("claude", $"mcp add --scope {scope} {McpServerName} -- \"{command}\" mcp");
                    break;
                case McpClientKind.Codex:
                    RejectProjectScope(client, project);
                    RunClientCli("codex", $"mcp remove {McpServerName}", ignoreFailure: true);
                    RunClientCli("codex", $"mcp add {McpServerName} -- \"{command}\" mcp");
                    break;
                case McpClientKind.Cursor:
                    UpdateJsonConfig(CursorConfigPath(project), "mcpServers", new JObject {
                        ["command"] = command,
                        ["args"] = new JArray("mcp"),
                    });
                    break;
                case McpClientKind.VSCode:
                    UpdateJsonConfig(VSCodeConfigPath(project), "servers", new JObject {
                        ["type"] = "stdio",
                        ["command"] = command,
                        ["args"] = new JArray("mcp"),
                    });
                    break;
                case McpClientKind.OpenCode:
                    UpdateJsonConfig(OpenCodeConfigPath(project), "mcp", new JObject {
                        ["type"] = "local",
                        ["command"] = new JArray(command, "mcp"),
                        ["enabled"] = true,
                    });
                    break;
            }

            Console.WriteLine($"Registered MCP server \"{McpServerName}\" ({command} mcp) with {client}.");
            if (PyRevitConfigs.GetAgentEnabled())
                Console.WriteLine("Agent host remains enabled. Reload pyRevit or restart Revit, then restart the MCP client.");
            else
                Console.WriteLine("Enable the agent host with 'pyrevit configs agent enable', reload pyRevit or restart Revit, then restart the MCP client.");
        }

        public static void UninstallMcp(McpClientKind client, bool project) {
            switch (client) {
                case McpClientKind.Claude:
                    RunClientCli("claude", $"mcp remove --scope {(project ? "project" : "user")} {McpServerName}");
                    break;
                case McpClientKind.Codex:
                    RejectProjectScope(client, project);
                    RunClientCli("codex", $"mcp remove {McpServerName}");
                    break;
                case McpClientKind.Cursor:
                    UpdateJsonConfig(CursorConfigPath(project), "mcpServers", null);
                    break;
                case McpClientKind.VSCode:
                    UpdateJsonConfig(VSCodeConfigPath(project), "servers", null);
                    break;
                case McpClientKind.OpenCode:
                    UpdateJsonConfig(OpenCodeConfigPath(project), "mcp", null);
                    break;
            }
            Console.WriteLine($"Removed MCP server \"{McpServerName}\" from {client}.");
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
            foreach (McpClientKind client in Enum.GetValues(typeof(McpClientKind))) {
                try {
                    if (IsClientCliManaged(client))
                        UninstallCliManagedClient(client, ownedOnly);
                    else if (!ownedOnly)
                        UninstallMcp(client, project: false);
                    else
                        UninstallOwnedFileRegistration(client, UserConfigPath(client));
                }
                catch (Exception ex) {
                    Console.WriteLine($"Skipped {client}: {ex.Message}");
                }
            }
        }

        private static void UninstallCliManagedClient(McpClientKind client, bool ownedOnly) {
            if (ownedOnly && !IsThisInstall(ReadCliClientCommand(client))) {
                Console.WriteLine($"Kept {client}: not registered to {Environment.ProcessPath}.");
                return;
            }
            if (ownedOnly && IsElevated()) {
                Console.WriteLine($"Kept {client}: an elevated cleanup doesn't run its command line tool. Run 'pyrevit mcp uninstall {client.ToString().ToLowerInvariant()}' from a normal prompt.");
                return;
            }
            UninstallMcp(client, project: false);
        }

        private static void UninstallOwnedFileRegistration(McpClientKind client, string path) {
            try {
                var registered = ReadFileClientCommand(client, path);
                if (!IsThisInstall(registered)) {
                    Console.WriteLine($"Kept {client} in {path}: not registered to {Environment.ProcessPath}.");
                    return;
                }
                UpdateJsonConfig(path, ServersKey(client), null);
                Console.WriteLine($"Removed MCP server \"{McpServerName}\" from {client} ({path}).");
            }
            catch (Exception ex) {
                Console.WriteLine($"Skipped {client} in {path}: {ex.Message}");
            }
        }

        private static bool IsClientCliManaged(McpClientKind client) {
            return client == McpClientKind.Claude || client == McpClientKind.Codex;
        }

        private static bool IsElevated() {
            using (var identity = System.Security.Principal.WindowsIdentity.GetCurrent()) {
                return new System.Security.Principal.WindowsPrincipal(identity)
                    .IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
            }
        }

        private static bool IsThisInstall(string registered) {
            var current = Environment.ProcessPath;
            if (string.IsNullOrWhiteSpace(registered) || string.IsNullOrWhiteSpace(current))
                return false;
            try {
                return string.Equals(Path.GetFullPath(registered.Trim()), Path.GetFullPath(current), StringComparison.OrdinalIgnoreCase);
            }
            catch (Exception) {
                return false;
            }
        }

        private static string ReadCliClientCommand(McpClientKind client) {
            var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            switch (client) {
                case McpClientKind.Claude:
                    return TryReadJson(Path.Combine(userProfile, ".claude.json"))?["mcpServers"]?[McpServerName]?.Value<string>("command");
                case McpClientKind.Codex:
                    return ReadCodexCommand(Path.Combine(userProfile, ".codex", "config.toml"));
                default:
                    return null;
            }
        }

        private static string ReadFileClientCommand(McpClientKind client, string path) {
            var entry = TryReadJson(path)?[ServersKey(client)]?[McpServerName];
            if (client == McpClientKind.OpenCode)
                return (entry?["command"] as JArray)?.FirstOrDefault()?.Value<string>();
            return entry?.Value<string>("command");
        }

        private static string ServersKey(McpClientKind client) {
            switch (client) {
                case McpClientKind.Cursor:
                    return "mcpServers";
                case McpClientKind.VSCode:
                    return "servers";
                case McpClientKind.OpenCode:
                    return "mcp";
                default:
                    throw new ArgumentOutOfRangeException(nameof(client));
            }
        }

        private static string UserConfigPath(McpClientKind client) {
            return UserConfigPath(
                client,
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData));
        }

        private static string UserConfigPath(McpClientKind client, string home, string appData) {
            switch (client) {
                case McpClientKind.Cursor:
                    return Path.Combine(home, ".cursor", "mcp.json");
                case McpClientKind.VSCode:
                    return Path.Combine(appData, "Code", "User", "mcp.json");
                case McpClientKind.OpenCode:
                    return OpenCodeConfigFile(Path.Combine(home, ".config", "opencode"));
                default:
                    throw new ArgumentOutOfRangeException(nameof(client));
            }
        }

        private static string ReadCodexCommand(string path) {
            if (!File.Exists(path))
                return null;
            var section = Regex.Match(
                File.ReadAllText(path),
                @"^\[mcp_servers\." + McpServerName + @"\]\s*\n(?:(?!\[).*\n)*?command\s*=\s*(?:""(?<basic>(?:[^""\\]|\\.)*)""|'(?<literal>[^']*)')",
                RegexOptions.Multiline);
            if (!section.Success)
                return null;
            return section.Groups["literal"].Success
                ? section.Groups["literal"].Value
                : Regex.Unescape(section.Groups["basic"].Value);
        }

        private static void RejectProjectScope(McpClientKind client, bool project) {
            if (project)
                throw new PyRevitException(client + " only supports user-level MCP servers; drop --project.");
        }

        private static string CursorConfigPath(bool project) {
            return project
                ? Path.Combine(Environment.CurrentDirectory, ".cursor", "mcp.json")
                : UserConfigPath(McpClientKind.Cursor, Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), null);
        }

        /// <summary>
        /// OpenCode reads <c>opencode.jsonc</c> or <c>opencode.json</c>, globally from
        /// <c>~/.config/opencode</c> and per project from the project root. An existing file is
        /// updated; otherwise <c>opencode.json</c> is created.
        /// </summary>
        private static string OpenCodeConfigPath(bool project) {
            return OpenCodeConfigFile(project
                ? Environment.CurrentDirectory
                : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config", "opencode"));
        }

        private static string OpenCodeConfigFile(string directory) {
            var jsonc = Path.Combine(directory, "opencode.jsonc");
            return File.Exists(jsonc) ? jsonc : Path.Combine(directory, "opencode.json");
        }

        private static string VSCodeConfigPath(bool project) {
            return project
                ? Path.Combine(Environment.CurrentDirectory, ".vscode", "mcp.json")
                : UserConfigPath(McpClientKind.VSCode, null, Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData));
        }

        /// <summary>
        /// Adds (or with a null <paramref name="entry"/>, removes) the pyrevit server under
        /// <paramref name="serversKey"/> and leaves every other key untouched.
        /// </summary>
        private static void UpdateJsonConfig(string path, string serversKey, JObject entry) {
            var config = File.Exists(path) ? TryReadJson(path) : new JObject();
            if (config == null)
                throw new PyRevitException("Could not parse " + path + "; fix or remove it and retry.");
            if (File.Exists(path) && HasComments(path))
                throw new PyRevitException(
                    path + " contains comments, which rewriting it would drop. Add this under \""
                    + serversKey + "\" by hand instead:\n\"" + McpServerName + "\": "
                    + (entry ?? new JObject()).ToString(Formatting.Indented));

            var servers = config[serversKey] as JObject;
            if (servers == null) {
                if (entry == null)
                    return;
                servers = new JObject();
                config[serversKey] = servers;
            }

            if (entry == null)
                servers.Remove(McpServerName);
            else
                servers[McpServerName] = entry;

            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, config.ToString(Formatting.Indented), Utf8);
            Console.WriteLine("Updated " + path);
        }

        /// <summary>
        /// Runs a client's own CLI (<c>claude</c>, <c>codex</c>) by full path.
        /// </summary>
        /// <remarks>
        /// This command is often launched from Revit (Settings → Agent Runtime), and Revit's
        /// environment keeps the PATH from when Revit started, which misses tools installed since.
        /// So the tool is located on the PATH freshly read from the registry plus the usual install
        /// folders, and the child process gets that fresh PATH too.
        /// </remarks>
        private static void RunClientCli(string tool, string arguments, bool ignoreFailure = false) {
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

        private static bool HasComments(string path) {
            var text = File.ReadAllText(path);
            var inString = false;
            for (var i = 0; i < text.Length - 1; i++) {
                var current = text[i];
                if (inString) {
                    if (current == '\\')
                        i++;
                    else if (current == '"')
                        inString = false;
                }
                else if (current == '"')
                    inString = true;
                else if (current == '/' && (text[i + 1] == '/' || text[i + 1] == '*'))
                    return true;
            }
            return false;
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

        private static JObject TryReadJson(string path) {
            try {
                return File.Exists(path) ? JObject.Parse(File.ReadAllText(path)) : null;
            }
            catch (Exception) {
                return null;
            }
        }
    }
}
