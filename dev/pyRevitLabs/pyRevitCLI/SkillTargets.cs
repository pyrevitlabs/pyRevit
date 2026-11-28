using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using pyRevitLabs.Common;

namespace pyRevitCLI {
    internal enum SkillScope {
        Project,
        User,
    }

    /// <summary>
    /// How <c>install</c> treats folders it must not simply overwrite.
    /// </summary>
    internal readonly struct SkillOptions {
        /// <summary>Replaces an owned copy that was edited or holds extra files.</summary>
        public bool Force { get; init; }

        /// <summary>Installs a skill whose plain name is taken as <c>pyrevit-&lt;name&gt;</c>.</summary>
        public bool Prefix { get; init; }
    }

    /// <summary>
    /// One skills folder and the target names that share it.
    /// </summary>
    internal sealed class SkillDestination {
        public string Label { get; set; }
        public string SkillsDir { get; set; }
    }

    /// <summary>
    /// The validated arguments every <c>agent skills</c> verb shares: where to write and where the
    /// shipped skills are.
    /// </summary>
    /// <remarks>
    /// This is the one owner of the scope rules. It takes the project folder, the profile folder and the
    /// shipped skills folder as arguments and never reads them from the environment.
    /// </remarks>
    internal sealed class SkillContext {
        private string[] targets;

        public SkillScope Scope { get; private set; }
        public string BaseRoot { get; private set; }
        public string ShippedDir { get; private set; }
        public IReadOnlyList<SkillDestination> Destinations { get; private set; }

        /// <summary>
        /// Whether <paramref name="target"/> was among the chosen targets.
        /// </summary>
        public bool Includes(string target) {
            return targets.Contains(target, StringComparer.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Validates the command line values and resolves the skills folders for <c>install</c> and <c>status</c>.
        /// </summary>
        /// <param name="targets">Comma-separated target names.</param>
        /// <param name="scope"><c>project</c> or <c>user</c>.</param>
        /// <param name="path">The project folder given with <c>--path</c>, or null.</param>
        /// <param name="currentFolder">The project folder when <paramref name="path"/> is null.</param>
        /// <param name="home">The user profile folder.</param>
        /// <param name="shippedDir">The shipped skills folder, or null when it was not found; the run then fails with a clear message.</param>
        /// <exception cref="PyRevitException">
        /// An unknown target or scope, <paramref name="path"/> together with the user scope, a missing project
        /// folder, or a profile folder that cannot be resolved.
        /// </exception>
        public static SkillContext Create(string targets, string scope, string path, string currentFolder, string home, string shippedDir) {
            var names = SkillTargets.ParseTargets(targets);
            var parsedScope = SkillTargets.ParseScope(scope);
            string baseRoot;
            if (parsedScope == SkillScope.Project) {
                var root = path ?? currentFolder;
                if (string.IsNullOrWhiteSpace(root) || !Directory.Exists(root))
                    throw new PyRevitException($"Project folder not found: {root}");
                baseRoot = Path.GetFullPath(root);
                var skillsFolder = SkillTargets.EndingSkillsFolder(baseRoot);
                if (skillsFolder != null)
                    throw new PyRevitException($"--path is the project folder, not a skills folder: {baseRoot} ends in {skillsFolder}. Pass the folder that contains it.");
            }
            else {
                if (path != null)
                    throw new PyRevitException("--path is the project folder and cannot be combined with --scope=user.");
                if (string.IsNullOrWhiteSpace(home) || !Directory.Exists(home))
                    throw new PyRevitException("The user profile folder cannot be resolved, so the user-level skills folder is unknown.");
                baseRoot = Path.GetFullPath(home);
            }
            return new SkillContext {
                targets = names,
                Scope = parsedScope,
                BaseRoot = baseRoot,
                ShippedDir = shippedDir,
                Destinations = SkillTargets.Destinations(names, parsedScope, baseRoot),
            };
        }

        /// <summary>
        /// Same as <see cref="Create"/> for <c>uninstall</c>, which does not need the shipped skills.
        /// </summary>
        public static SkillContext CreateForUninstall(string targets, string scope, string path, string currentFolder, string home) {
            return Create(targets, scope, path, currentFolder, home, null);
        }
    }

    /// <summary>
    /// The skill folders each client reads, and the warning for a skill installed where one client reads it twice.
    /// </summary>
    internal static class SkillTargets {
        internal static readonly string[] TargetNames = { "agents", "antigravity", "claude", "copilot", "opencode" };

        private static readonly Dictionary<string, (string[] Project, string[] User)> Folders =
            new Dictionary<string, (string[] Project, string[] User)>(StringComparer.OrdinalIgnoreCase) {
                ["agents"] = (new[] { ".agents", "skills" }, new[] { ".agents", "skills" }),
                ["antigravity"] = (new[] { ".agents", "skills" }, new[] { ".gemini", "config", "skills" }),
                ["claude"] = (new[] { ".claude", "skills" }, new[] { ".claude", "skills" }),
                ["copilot"] = (new[] { ".github", "skills" }, new[] { ".copilot", "skills" }),
                ["opencode"] = (new[] { ".opencode", "skills" }, new[] { ".config", "opencode", "skills" }),
            };

        private static readonly (string Client, string[][] Project, string[][] User)[] ClientReads = {
            ("OpenCode",
                new[] { new[] { ".opencode", "skills" }, new[] { ".claude", "skills" }, new[] { ".agents", "skills" } },
                new[] { new[] { ".config", "opencode", "skills" }, new[] { ".claude", "skills" }, new[] { ".agents", "skills" } }),
            ("Cursor",
                new[] { new[] { ".agents", "skills" }, new[] { ".cursor", "skills" }, new[] { ".claude", "skills" }, new[] { ".codex", "skills" } },
                new[] { new[] { ".agents", "skills" }, new[] { ".cursor", "skills" }, new[] { ".claude", "skills" }, new[] { ".codex", "skills" } }),
            ("VS Code",
                new[] { new[] { ".github", "skills" }, new[] { ".claude", "skills" }, new[] { ".agents", "skills" } },
                new[] { new[] { ".copilot", "skills" }, new[] { ".claude", "skills" }, new[] { ".agents", "skills" } }),
        };

        /// <summary>
        /// Splits a comma-separated <c>--target</c> value into valid, distinct target names.
        /// </summary>
        /// <exception cref="PyRevitException">The value is empty or names an unknown target.</exception>
        internal static string[] ParseTargets(string text) {
            var names = (text ?? string.Empty).Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(name => name.Trim().ToLowerInvariant())
                .Distinct()
                .ToArray();
            var unknown = names.Where(name => !Folders.ContainsKey(name)).ToList();
            if (names.Length == 0 || unknown.Count > 0)
                throw new PyRevitException(
                    $"Unknown target '{(unknown.Count > 0 ? string.Join(",", unknown) : text)}'. Valid targets: {string.Join(", ", TargetNames)}.");
            return names;
        }

        internal static SkillScope ParseScope(string text) {
            switch ((text ?? string.Empty).ToLowerInvariant()) {
                case "project": return SkillScope.Project;
                case "user": return SkillScope.User;
                default: throw new PyRevitException($"Unknown scope '{text}'. Valid scopes: project, user.");
            }
        }

        internal static List<SkillDestination> Destinations(string[] names, SkillScope scope, string baseRoot) {
            return names
                .Select(name => (Name: name, Dir: SkillsDir(baseRoot, scope == SkillScope.Project ? Folders[name].Project : Folders[name].User)))
                .GroupBy(entry => entry.Dir, StringComparer.OrdinalIgnoreCase)
                .Select(group => new SkillDestination { Label = string.Join("+", group.Select(entry => entry.Name)), SkillsDir = group.Key })
                .ToList();
        }

        /// <summary>
        /// The project-level skills folder (such as <c>.agents/skills</c>) that <paramref name="path"/> ends in, or null.
        /// </summary>
        internal static string EndingSkillsFolder(string path) {
            var segments = path.Split(new[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar }, StringSplitOptions.RemoveEmptyEntries);
            return Folders.Values
                .Select(folder => folder.Project)
                .Where(parts => segments.Length >= parts.Length && segments.Skip(segments.Length - parts.Length).SequenceEqual(parts, StringComparer.OrdinalIgnoreCase))
                .Select(parts => string.Join(Path.DirectorySeparatorChar.ToString(), parts))
                .FirstOrDefault();
        }

        private static string SkillsDir(string baseRoot, string[] parts) {
            return Path.Combine(new[] { baseRoot }.Concat(parts).ToArray());
        }

        /// <summary>
        /// Warns when a client that reads several skill folders would see the same pyRevit-owned skill more than once.
        /// </summary>
        internal static void WarnOverlaps(SkillContext context, List<string> warnings) {
            foreach (var (client, project, user) in ClientReads) {
                var owners = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
                foreach (var parts in context.Scope == SkillScope.Project ? project : user) {
                    foreach (var (directory, key) in SkillFiles.FindOwnedFolders(context.BaseRoot, SkillsDir(context.BaseRoot, parts))) {
                        if (!owners.TryGetValue(key, out var folders))
                            owners[key] = folders = new List<string>();
                        folders.Add(directory);
                    }
                }
                foreach (var entry in owners.Where(entry => entry.Value.Count > 1).OrderBy(entry => entry.Key, StringComparer.Ordinal))
                    warnings.Add($"{client} reads '{entry.Key}' from {entry.Value.Count} folders ({string.Join(", ", entry.Value)}); keep one copy.");
            }
        }
    }
}
