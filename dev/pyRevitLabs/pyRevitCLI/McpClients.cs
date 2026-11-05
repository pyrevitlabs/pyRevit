using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

using Console = Colorful.Console;

namespace pyRevitCLI {
    /// <summary>
    /// One MCP client that <c>pyrevit mcp install|uninstall</c> can register the pyrevit server with.
    /// </summary>
    /// <remarks>
    /// Adding a client means adding a subclass to <see cref="All"/>; nothing else switches on
    /// <see cref="McpClientKind"/>.
    /// </remarks>
    internal abstract class McpClient {
        public static readonly IReadOnlyList<McpClient> All = new McpClient[] {
            new ClaudeMcpClient(),
            new CodexMcpClient(),
            new CursorMcpClient(),
            new VSCodeMcpClient(),
            new OpenCodeMcpClient(),
        };

        public static McpClient For(McpClientKind kind) {
            return All.First(client => client.Kind == kind);
        }

        public abstract McpClientKind Kind { get; }

        public abstract void Install(string command, bool project);

        public void Uninstall(bool project) {
            RemoveRegistration(project);
            Console.WriteLine($"Removed MCP server \"{PyRevitCLIAgentCmds.McpServerName}\" from {Kind}.");
        }

        /// <summary>
        /// Removes the user-level registration for the uninstaller.
        /// </summary>
        /// <param name="ownedOnly">
        /// Keeps a registration whose command is not this <c>pyrevit.exe</c>, or can't be read.
        /// </param>
        /// <remarks>
        /// Without <paramref name="ownedOnly"/> the running account's configs are used, whatever
        /// <paramref name="home"/> and <paramref name="appData"/> say.
        /// </remarks>
        public abstract void UninstallFromUserProfile(bool ownedOnly, string home, string appData);

        protected abstract void RemoveRegistration(bool project);

        protected static bool IsThisInstall(string registered) {
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
    }

    /// <summary>
    /// A client configured through its own command line tool.
    /// </summary>
    internal abstract class CliMcpClient : McpClient {
        protected abstract string Tool { get; }

        protected virtual bool SupportsProjectScope => true;

        protected abstract string AddArguments(string command, bool project);

        protected abstract string RemoveArguments(bool project);

        protected abstract string ReadRegisteredCommand(string home);

        public override void Install(string command, bool project) {
            RejectUnsupportedScope(project);
            PyRevitCLIAgentCmds.ClientCli(Tool, RemoveArguments(project), true);
            PyRevitCLIAgentCmds.ClientCli(Tool, AddArguments(command, project), false);
        }

        protected override void RemoveRegistration(bool project) {
            RejectUnsupportedScope(project);
            PyRevitCLIAgentCmds.ClientCli(Tool, RemoveArguments(project), false);
        }

        public override void UninstallFromUserProfile(bool ownedOnly, string home, string appData) {
            if (ownedOnly && !IsThisInstall(ReadRegisteredCommand(home))) {
                Console.WriteLine($"Kept {Kind}: not registered to {Environment.ProcessPath}.");
                return;
            }
            if (ownedOnly && IsElevated()) {
                Console.WriteLine($"Kept {Kind}: an elevated cleanup doesn't run its command line tool. Run 'pyrevit mcp uninstall {Kind.ToString().ToLowerInvariant()}' from a normal prompt.");
                return;
            }
            Uninstall(project: false);
        }

        private void RejectUnsupportedScope(bool project) {
            if (project && !SupportsProjectScope)
                throw new PyRevitException(Kind + " only supports user-level MCP servers; drop --project.");
        }

        private static bool IsElevated() {
            using (var identity = System.Security.Principal.WindowsIdentity.GetCurrent()) {
                return new System.Security.Principal.WindowsPrincipal(identity)
                    .IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
            }
        }
    }

    internal sealed class ClaudeMcpClient : CliMcpClient {
        public override McpClientKind Kind => McpClientKind.Claude;

        protected override string Tool => "claude";

        protected override string AddArguments(string command, bool project) {
            return $"mcp add --scope {Scope(project)} {PyRevitCLIAgentCmds.McpServerName} -- \"{command}\" mcp";
        }

        protected override string RemoveArguments(bool project) {
            return $"mcp remove --scope {Scope(project)} {PyRevitCLIAgentCmds.McpServerName}";
        }

        protected override string ReadRegisteredCommand(string home) {
            return PyRevitCLIAgentCmds.TryReadJson(Path.Combine(home, ".claude.json"))
                ?["mcpServers"]?[PyRevitCLIAgentCmds.McpServerName]?.Value<string>("command");
        }

        private static string Scope(bool project) {
            return project ? "project" : "user";
        }
    }

    internal sealed class CodexMcpClient : CliMcpClient {
        public override McpClientKind Kind => McpClientKind.Codex;

        protected override string Tool => "codex";

        protected override bool SupportsProjectScope => false;

        protected override string AddArguments(string command, bool project) {
            return $"mcp add {PyRevitCLIAgentCmds.McpServerName} -- \"{command}\" mcp";
        }

        protected override string RemoveArguments(bool project) {
            return $"mcp remove {PyRevitCLIAgentCmds.McpServerName}";
        }

        protected override string ReadRegisteredCommand(string home) {
            var path = Path.Combine(home, ".codex", "config.toml");
            if (!File.Exists(path))
                return null;
            var section = Regex.Match(
                File.ReadAllText(path),
                @"^\[mcp_servers\." + PyRevitCLIAgentCmds.McpServerName + @"\]\s*\n(?:(?!\[).*\n)*?command\s*=\s*(?:""(?<basic>(?:[^""\\]|\\.)*)""|'(?<literal>[^']*)')",
                RegexOptions.Multiline);
            if (!section.Success)
                return null;
            return section.Groups["literal"].Success
                ? section.Groups["literal"].Value
                : Regex.Unescape(section.Groups["basic"].Value);
        }
    }

    /// <summary>
    /// A client configured through a JSON file, updated in place so other servers in it are kept.
    /// </summary>
    internal abstract class JsonFileMcpClient : McpClient {
        private static readonly Encoding Utf8 = new UTF8Encoding(false);

        protected abstract string ServersKey { get; }

        protected abstract JObject Entry(string command);

        protected abstract string ProjectConfigPath();

        protected abstract string UserConfigPath(string home, string appData);

        protected virtual string RegisteredCommand(JToken entry) {
            return entry?.Value<string>("command");
        }

        public override void Install(string command, bool project) {
            UpdateJsonConfig(ConfigPath(project), ServersKey, Entry(command));
        }

        protected override void RemoveRegistration(bool project) {
            UpdateJsonConfig(ConfigPath(project), ServersKey, null);
        }

        public override void UninstallFromUserProfile(bool ownedOnly, string home, string appData) {
            if (!ownedOnly) {
                Uninstall(project: false);
                return;
            }

            var path = UserConfigPath(home, appData);
            try {
                var registered = RegisteredCommand(PyRevitCLIAgentCmds.TryReadJson(path)?[ServersKey]?[PyRevitCLIAgentCmds.McpServerName]);
                if (!IsThisInstall(registered)) {
                    if (registered != null)
                        Console.WriteLine($"Kept {Kind} in {path}: not registered to {Environment.ProcessPath}.");
                    return;
                }
                UpdateJsonConfig(path, ServersKey, null);
                Console.WriteLine($"Removed MCP server \"{PyRevitCLIAgentCmds.McpServerName}\" from {Kind} ({path}).");
            }
            catch (Exception ex) {
                Console.WriteLine($"Skipped {Kind} in {path}: {ex.Message}");
            }
        }

        private string ConfigPath(bool project) {
            return project
                ? ProjectConfigPath()
                : UserConfigPath(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData));
        }

        /// <summary>
        /// Adds (or with a null <paramref name="entry"/>, removes) the pyrevit server under
        /// <paramref name="serversKey"/> and leaves every other key untouched.
        /// </summary>
        private static void UpdateJsonConfig(string path, string serversKey, JObject entry) {
            var serverName = PyRevitCLIAgentCmds.McpServerName;
            var config = File.Exists(path) ? PyRevitCLIAgentCmds.TryReadJson(path) : new JObject();
            if (config == null)
                throw new PyRevitException("Could not parse " + path + "; fix or remove it and retry.");
            if (File.Exists(path) && HasComments(path))
                throw new PyRevitException(
                    path + " contains comments, which rewriting it would drop. Add this under \""
                    + serversKey + "\" by hand instead:\n\"" + serverName + "\": "
                    + (entry ?? new JObject()).ToString(Formatting.Indented));

            var servers = config[serversKey] as JObject;
            if (servers == null) {
                if (entry == null)
                    return;
                servers = new JObject();
                config[serversKey] = servers;
            }

            if (entry == null)
                servers.Remove(serverName);
            else
                servers[serverName] = entry;

            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, config.ToString(Formatting.Indented), Utf8);
            Console.WriteLine("Updated " + path);
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
    }

    internal sealed class CursorMcpClient : JsonFileMcpClient {
        public override McpClientKind Kind => McpClientKind.Cursor;

        protected override string ServersKey => "mcpServers";

        protected override JObject Entry(string command) {
            return new JObject {
                ["command"] = command,
                ["args"] = new JArray("mcp"),
            };
        }

        protected override string ProjectConfigPath() {
            return Path.Combine(Environment.CurrentDirectory, ".cursor", "mcp.json");
        }

        protected override string UserConfigPath(string home, string appData) {
            return Path.Combine(home, ".cursor", "mcp.json");
        }
    }

    internal sealed class VSCodeMcpClient : JsonFileMcpClient {
        public override McpClientKind Kind => McpClientKind.VSCode;

        protected override string ServersKey => "servers";

        protected override JObject Entry(string command) {
            return new JObject {
                ["type"] = "stdio",
                ["command"] = command,
                ["args"] = new JArray("mcp"),
            };
        }

        protected override string ProjectConfigPath() {
            return Path.Combine(Environment.CurrentDirectory, ".vscode", "mcp.json");
        }

        protected override string UserConfigPath(string home, string appData) {
            return Path.Combine(appData, "Code", "User", "mcp.json");
        }
    }

    /// <summary>
    /// OpenCode reads <c>opencode.jsonc</c> or <c>opencode.json</c>, globally from
    /// <c>~/.config/opencode</c> and per project from the project root. An existing file is
    /// updated; otherwise <c>opencode.json</c> is created.
    /// </summary>
    internal sealed class OpenCodeMcpClient : JsonFileMcpClient {
        public override McpClientKind Kind => McpClientKind.OpenCode;

        protected override string ServersKey => "mcp";

        protected override JObject Entry(string command) {
            return new JObject {
                ["type"] = "local",
                ["command"] = new JArray(command, "mcp"),
                ["enabled"] = true,
            };
        }

        protected override string RegisteredCommand(JToken entry) {
            return (entry?["command"] as JArray)?.FirstOrDefault()?.Value<string>();
        }

        protected override string ProjectConfigPath() {
            return ConfigFile(Environment.CurrentDirectory);
        }

        protected override string UserConfigPath(string home, string appData) {
            return ConfigFile(Path.Combine(home, ".config", "opencode"));
        }

        private static string ConfigFile(string directory) {
            var jsonc = Path.Combine(directory, "opencode.jsonc");
            return File.Exists(jsonc) ? jsonc : Path.Combine(directory, "opencode.json");
        }
    }
}
