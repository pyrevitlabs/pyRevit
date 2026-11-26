using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// One skill in one skills folder: what <c>agent skills install|status|uninstall</c> found or did.
    /// </summary>
    internal sealed class SkillAction {
        public string Target { get; set; }
        public string Skill { get; set; }
        public string State { get; set; }
        public string Folder { get; set; }
    }

    /// <summary>
    /// The outcome of an install, status or uninstall run, with the warnings to show the user.
    /// </summary>
    internal sealed class SkillsReport {
        public List<SkillAction> Actions { get; } = new List<SkillAction>();
        public List<string> Warnings { get; } = new List<string>();
    }

    /// <summary>
    /// Copies the shipped agent skills into the skill folders other coding agents read, and reports
    /// or removes those copies.
    /// </summary>
    /// <remarks>
    /// Only skills shipped with pyRevit are copied, never user skills or <c>INSTRUCTIONS.md</c>.
    /// Each copy carries a <c>.pyrevit-skill.json</c> marker; the marker is what makes a folder
    /// pyRevit-owned.
    /// Invariants: a folder without the marker is never overwritten, replaced or deleted; no path
    /// is written, replaced or deleted through a link (reparse point), and every path stays inside
    /// the skills folder; a copy is built in a temporary folder beside its destination and moved
    /// into place, so a failed run leaves the old copy. The core takes the project root, the
    /// profile folder and the shipped skills folder as arguments and never reads them from the
    /// environment.
    /// Installed copies are guidance, not policy: they cannot change host policy.
    /// </remarks>
    internal static class PyRevitAgentSkillInstaller {
        public const string MarkerFile = ".pyrevit-skill.json";
        public const string ScopeProject = "project";
        public const string ScopeUser = "user";
        public const int MaxDescriptionChars = 240;
        private const string SkillFile = "SKILL.md";
        private const string TempPrefix = ".pyrevit-tmp-";
        private const string NamePrefix = "pyrevit-";
        private const int MaxFileBytes = 128 * 1024;
        private const int MaxFilesPerSkill = 256;
        private const int MaxMarkerBytes = 4 * 1024;
        private static readonly Regex SkillName = new Regex("^[a-z0-9][a-z0-9-]{0,63}\\z", RegexOptions.Compiled);

        private static readonly Dictionary<string, (string[] Project, string[] User)> TargetFolders =
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

        private enum Found { Missing, Foreign, Current, Stale, Edited }

        private sealed class ShippedSkill {
            public string Name { get; set; }
            public string Directory { get; set; }
            public List<(string Relative, string Path)> Files { get; set; }
            public string Digest { get; set; }
        }

        private sealed class Destination {
            public string Label { get; set; }
            public string BaseRoot { get; set; }
            public string SkillsDir { get; set; }
        }

        /// <summary>
        /// Splits a comma-separated <c>--target</c> value into valid, distinct target names.
        /// </summary>
        /// <exception cref="PyRevitException">The value is empty or names an unknown target.</exception>
        public static string[] ParseTargets(string text) {
            var names = (text ?? string.Empty).Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(name => name.Trim().ToLowerInvariant())
                .Distinct()
                .ToArray();
            var unknown = names.Where(name => !TargetFolders.ContainsKey(name)).ToList();
            if (names.Length == 0 || unknown.Count > 0)
                throw new PyRevitException(
                    $"Unknown target '{(unknown.Count > 0 ? string.Join(",", unknown) : text)}'. Valid targets: {string.Join(", ", TargetFolders.Keys)}.");
            return names;
        }

        /// <summary>
        /// Installs the shipped skills into the skills folder of each target.
        /// </summary>
        /// <param name="force">
        /// Replaces a pyRevit-owned copy whose files were edited by hand. It never touches a folder
        /// without the marker.
        /// </param>
        /// <param name="prefix">
        /// Installs a skill whose plain name is taken by a folder pyRevit did not write as
        /// <c>pyrevit-&lt;name&gt;</c>, rewriting the <c>name</c> front matter line to match.
        /// </param>
        /// <remarks>
        /// Idempotent: a current copy is reported and not rewritten, a stale owned copy is refreshed,
        /// a folder without the marker is skipped with a warning. Writes only below the skills folders.
        /// </remarks>
        /// <exception cref="PyRevitException">
        /// An unknown scope, a missing project root or profile, a link on the way to a skills folder, or a
        /// shipped file over 128 KiB.
        /// </exception>
        public static SkillsReport Install(IEnumerable<string> targets, string scope, string projectRoot, string home, string shippedSkillsDir, bool force, bool prefix) {
            var report = new SkillsReport();
            var destinations = Resolve(targets, scope, projectRoot, home);
            var shipped = LoadShipped(shippedSkillsDir, report);
            foreach (var destination in destinations) {
                var exists = EnsureSkillsDirSafe(destination);
                foreach (var skill in shipped) {
                    var name = skill.Name;
                    var found = exists ? Inspect(Path.Combine(destination.SkillsDir, name), skill) : Found.Missing;
                    if (found == Found.Foreign && prefix && !name.StartsWith(NamePrefix, StringComparison.Ordinal)) {
                        name = NamePrefix + name;
                        found = SkillName.IsMatch(name) ? Inspect(Path.Combine(destination.SkillsDir, name), skill) : Found.Foreign;
                    }
                    var folder = Path.Combine(destination.SkillsDir, name);
                    string state;
                    if (found == Found.Foreign) {
                        state = "foreign";
                        report.Warnings.Add($"Skipped '{skill.Name}': {folder} exists and was not installed by pyRevit. Use --prefix to install it as {NamePrefix}{skill.Name}.");
                    }
                    else if (found == Found.Current)
                        state = "current";
                    else if (found == Found.Edited && !force) {
                        state = "edited";
                        report.Warnings.Add($"Skipped '{skill.Name}': {folder} was edited by hand. Use --force to replace it.");
                    }
                    else {
                        WriteSkill(destination, skill, name, replace: found != Found.Missing, report);
                        state = found == Found.Missing ? "installed" : "updated";
                    }
                    report.Actions.Add(new SkillAction { Target = destination.Label, Skill = skill.Name, State = state, Folder = folder });
                    if (state == "installed" || state == "updated" || state == "current")
                        WarnLongDescription(folder, report);
                }
            }
            return report;
        }

        /// <summary>
        /// Compares the copies in each target's skills folder with the shipped skills.
        /// </summary>
        /// <remarks>
        /// States: <c>current</c>, <c>stale</c> (shipped skill changed), <c>edited</c> (files differ from
        /// the marker), <c>missing</c>, <c>foreign</c> (a folder pyRevit did not write holds the name).
        /// Also warns when one client would read the same pyRevit-owned skill from several folders.
        /// Read-only.
        /// </remarks>
        public static SkillsReport Status(IEnumerable<string> targets, string scope, string projectRoot, string home, string shippedSkillsDir) {
            var report = new SkillsReport();
            var destinations = Resolve(targets, scope, projectRoot, home);
            var shipped = LoadShipped(shippedSkillsDir, report);
            foreach (var destination in destinations) {
                var exists = EnsureSkillsDirSafe(destination, create: false);
                foreach (var skill in shipped) {
                    var folder = Path.Combine(destination.SkillsDir, skill.Name);
                    var found = exists ? Inspect(folder, skill) : Found.Missing;
                    if (found == Found.Foreign || found == Found.Missing) {
                        var prefixed = Path.Combine(destination.SkillsDir, NamePrefix + skill.Name);
                        var prefixedFound = exists && !skill.Name.StartsWith(NamePrefix, StringComparison.Ordinal) && SkillName.IsMatch(NamePrefix + skill.Name)
                            ? Inspect(prefixed, skill)
                            : Found.Missing;
                        if (prefixedFound != Found.Missing && prefixedFound != Found.Foreign) {
                            found = prefixedFound;
                            folder = prefixed;
                        }
                    }
                    report.Actions.Add(new SkillAction { Target = destination.Label, Skill = skill.Name, State = found.ToString().ToLowerInvariant(), Folder = folder });
                    if (found == Found.Current || found == Found.Stale || found == Found.Edited)
                        WarnLongDescription(folder, report);
                }
            }
            WarnOverlappingFolders(scope, projectRoot, home, report);
            return report;
        }

        /// <summary>
        /// Removes the pyRevit-owned skill folders from each target's skills folder.
        /// </summary>
        /// <remarks>
        /// Removes only folders with the marker, plus empty <c>.pyrevit-tmp-*</c> leftovers. Never removes
        /// the skills folder, a folder without the marker or anything reached through a link.
        /// </remarks>
        public static SkillsReport Uninstall(IEnumerable<string> targets, string scope, string projectRoot, string home) {
            var report = new SkillsReport();
            foreach (var destination in Resolve(targets, scope, projectRoot, home)) {
                if (!EnsureSkillsDirSafe(destination, create: false))
                    continue;
                foreach (var directory in Directory.GetDirectories(destination.SkillsDir).OrderBy(path => path, StringComparer.OrdinalIgnoreCase)) {
                    var name = Path.GetFileName(directory);
                    if (IsLink(directory))
                        continue;
                    if (name.StartsWith(TempPrefix, StringComparison.Ordinal)) {
                        if (!Directory.EnumerateFileSystemEntries(directory).Any())
                            Directory.Delete(directory);
                        continue;
                    }
                    if (ReadMarker(directory) == null)
                        continue;
                    if (ContainsLink(directory)) {
                        report.Warnings.Add($"Kept {directory}: it contains a link.");
                        continue;
                    }
                    Directory.Delete(directory, recursive: true);
                    report.Actions.Add(new SkillAction { Target = destination.Label, Skill = name, State = "removed", Folder = directory });
                }
            }
            return report;
        }

        /// <summary>
        /// Warns about every user skill whose description is over the limit agents handle well.
        /// </summary>
        public static List<string> UserSkillWarnings(string userSkillsDir) {
            var warnings = new List<string>();
            if (userSkillsDir == null || !Directory.Exists(userSkillsDir))
                return warnings;
            foreach (var directory in Directory.GetDirectories(userSkillsDir).Where(path => !IsLink(path)))
                WarnLongDescription(directory, warnings, "User skill");
            return warnings;
        }

        private static List<Destination> Resolve(IEnumerable<string> targets, string scope, string projectRoot, string home) {
            var names = targets.ToList();
            if (names.Count == 0 || names.Any(name => !TargetFolders.ContainsKey(name)))
                throw new PyRevitException($"Unknown target. Valid targets: {string.Join(", ", TargetFolders.Keys)}.");
            if (scope != ScopeProject && scope != ScopeUser)
                throw new PyRevitException($"Unknown scope '{scope}'. Valid scopes: {ScopeProject}, {ScopeUser}.");

            string baseRoot;
            if (scope == ScopeProject) {
                if (string.IsNullOrWhiteSpace(projectRoot) || !Directory.Exists(projectRoot))
                    throw new PyRevitException($"Project folder not found: {projectRoot}");
                baseRoot = Path.GetFullPath(projectRoot);
            }
            else {
                if (string.IsNullOrWhiteSpace(home) || !Directory.Exists(home))
                    throw new PyRevitException("The user profile folder cannot be resolved, so the user-level skills folder is unknown.");
                baseRoot = Path.GetFullPath(home);
            }

            return names
                .Select(name => (Name: name, Dir: Path.Combine(new[] { baseRoot }.Concat(scope == ScopeProject ? TargetFolders[name].Project : TargetFolders[name].User).ToArray())))
                .GroupBy(entry => entry.Dir, StringComparer.OrdinalIgnoreCase)
                .Select(group => new Destination { Label = string.Join("+", group.Select(entry => entry.Name)), BaseRoot = baseRoot, SkillsDir = group.Key })
                .ToList();
        }

        private static bool EnsureSkillsDirSafe(Destination destination, bool create = true) {
            AssertInside(destination.BaseRoot, destination.SkillsDir);
            AssertNoLink(destination.BaseRoot, destination.SkillsDir);
            if (Directory.Exists(destination.SkillsDir))
                return true;
            if (create)
                Directory.CreateDirectory(destination.SkillsDir);
            return create;
        }

        private static List<ShippedSkill> LoadShipped(string shippedSkillsDir, SkillsReport report) {
            if (string.IsNullOrWhiteSpace(shippedSkillsDir) || !Directory.Exists(shippedSkillsDir))
                throw new PyRevitException("The shipped agent skills were not found. Run this command from a pyRevit install or clone that has pyrevitlib/pyrevit/agent/skills.");
            var skills = new List<ShippedSkill>();
            foreach (var directory in Directory.GetDirectories(shippedSkillsDir).OrderBy(path => path, StringComparer.Ordinal)) {
                var skill = IsLink(directory) ? null : PyRevitAgentSkills.ReadSkill(directory, PyRevitAgentSkills.ShippedSource);
                if (skill == null)
                    continue;
                if (skill.Name != Path.GetFileName(directory)) {
                    report.Warnings.Add($"Skipped {directory}: the skill name '{skill.Name}' differs from its folder name.");
                    continue;
                }
                var files = CollectFiles(directory);
                skills.Add(new ShippedSkill { Name = skill.Name, Directory = directory, Files = files, Digest = Digest(files, null) });
            }
            return skills;
        }

        private static List<(string Relative, string Path)> CollectFiles(string root) {
            var files = new List<(string Relative, string Path)>();
            Collect(root, root, files);
            return files.OrderBy(file => file.Relative, StringComparer.Ordinal).ToList();
        }

        private static void Collect(string root, string directory, List<(string Relative, string Path)> files) {
            foreach (var file in Directory.GetFiles(directory, "*.md")) {
                if (IsLink(file))
                    continue;
                if (files.Count >= MaxFilesPerSkill)
                    throw new PyRevitException($"{root} has more than {MaxFilesPerSkill} markdown files.");
                if (new FileInfo(file).Length > MaxFileBytes)
                    throw new PyRevitException($"{file} is over the {MaxFileBytes / 1024} KiB limit.");
                files.Add((Path.GetRelativePath(root, file).Replace('\\', '/'), file));
            }
            foreach (var child in Directory.GetDirectories(directory))
                if (!IsLink(child))
                    Collect(root, child, files);
        }

        private static string Digest(List<(string Relative, string Path)> files, string restoreName) {
            using (var sha256 = IncrementalHash.CreateHash(HashAlgorithmName.SHA256)) {
                foreach (var file in files) {
                    var bytes = ReadFile(file, restoreName);
                    sha256.AppendData(Encoding.UTF8.GetBytes(file.Relative));
                    sha256.AppendData(new byte[] { 0 });
                    sha256.AppendData(BitConverter.GetBytes((long)bytes.Length));
                    sha256.AppendData(bytes);
                }
                return BitConverter.ToString(sha256.GetHashAndReset()).Replace("-", string.Empty).ToLowerInvariant();
            }
        }

        private static byte[] ReadFile((string Relative, string Path) file, string rename) {
            var bytes = File.ReadAllBytes(file.Path);
            return rename != null && file.Relative == SkillFile ? RenameSkill(bytes, rename) : bytes;
        }

        private static byte[] RenameSkill(byte[] bytes, string name) {
            var lines = new UTF8Encoding(false).GetString(bytes).Split('\n').ToList();
            for (var index = 1; index < lines.Count && lines[index].Trim() != "---"; index++) {
                if (lines[index].StartsWith("name:", StringComparison.OrdinalIgnoreCase)) {
                    lines[index] = "name: " + name + (lines[index].EndsWith("\r") ? "\r" : string.Empty);
                    return new UTF8Encoding(false).GetBytes(string.Join("\n", lines));
                }
            }
            throw new PyRevitException($"SKILL.md has no name line to rewrite for '{name}'.");
        }

        private static Found Inspect(string folder, ShippedSkill skill) {
            if (!IsLink(folder) && !Directory.Exists(folder))
                return Found.Missing;
            if (IsLink(folder))
                throw new PyRevitException($"Refusing {folder}: it is a link.");
            var marker = ReadMarker(folder);
            if (marker == null)
                return Found.Foreign;
            string installed;
            try {
                installed = Digest(CollectFiles(folder), Path.GetFileName(folder) == skill.Name ? null : skill.Name);
            }
            catch (Exception ex) when (ex is PyRevitException || ex is IOException || ex is UnauthorizedAccessException) {
                return Found.Edited;
            }
            if (installed != marker.Value<string>("sha256"))
                return Found.Edited;
            return marker.Value<string>("sha256") == skill.Digest ? Found.Current : Found.Stale;
        }

        private static JObject ReadMarker(string folder) {
            var path = Path.Combine(folder, MarkerFile);
            try {
                if (!File.Exists(path) || IsLink(path) || new FileInfo(path).Length > MaxMarkerBytes)
                    return null;
                var marker = JObject.Parse(File.ReadAllText(path));
                return marker.Value<string>("source") == PyRevitAgentSkills.ShippedSource && marker.Value<string>("sha256") != null ? marker : null;
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException || ex is pyRevitLabs.Json.JsonException) {
                return null;
            }
        }

        private static void WriteSkill(Destination destination, ShippedSkill skill, string installedName, bool replace, SkillsReport report) {
            var destinationFolder = Path.Combine(destination.SkillsDir, installedName);
            AssertInside(destination.SkillsDir, destinationFolder);
            var temp = Path.Combine(destination.SkillsDir, TempPrefix + Guid.NewGuid().ToString("N"));
            try {
                Directory.CreateDirectory(temp);
                var rename = installedName == skill.Name ? null : installedName;
                foreach (var file in skill.Files) {
                    var target = Path.Combine(temp, file.Relative.Replace('/', Path.DirectorySeparatorChar));
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    File.WriteAllBytes(target, ReadFile(file, rename));
                }
                var marker = new JObject { ["source"] = PyRevitAgentSkills.ShippedSource };
                var version = CurrentVersion();
                if (version != null)
                    marker["version"] = version;
                marker["sha256"] = skill.Digest;
                File.WriteAllText(Path.Combine(temp, MarkerFile), marker.ToString());

                if (!replace) {
                    Directory.Move(temp, destinationFolder);
                    return;
                }
                if (ContainsLink(destinationFolder))
                    throw new PyRevitException($"Refusing to replace {destinationFolder}: it contains a link.");
                var aside = Path.Combine(destination.SkillsDir, TempPrefix + Guid.NewGuid().ToString("N"));
                Directory.Move(destinationFolder, aside);
                try {
                    Directory.Move(temp, destinationFolder);
                }
                catch {
                    Directory.Move(aside, destinationFolder);
                    throw;
                }
                try {
                    Directory.Delete(aside, recursive: true);
                }
                catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
                    report.Warnings.Add($"Could not remove the old copy {aside}: {ex.Message}");
                }
            }
            finally {
                if (Directory.Exists(temp) && !IsLink(temp))
                    Directory.Delete(temp, recursive: true);
            }
        }

        private static string CurrentVersion() {
            var version = typeof(PyRevitAgentSkillInstaller).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion;
            if (string.IsNullOrWhiteSpace(version))
                return null;
            var plus = version.IndexOf('+');
            return plus > 0 ? version.Substring(0, plus) : version;
        }

        private static void WarnLongDescription(string folder, SkillsReport report) {
            WarnLongDescription(folder, report.Warnings, "Skill");
        }

        private static void WarnLongDescription(string folder, List<string> warnings, string label) {
            var path = Path.Combine(folder, SkillFile);
            try {
                if (!File.Exists(path) || IsLink(path) || new FileInfo(path).Length > MaxFileBytes)
                    return;
                var frontMatter = PyRevitAgentSkills.ParseFrontMatter(File.ReadAllLines(path));
                if (frontMatter.TryGetValue("description", out var description) && description.Length > MaxDescriptionChars)
                    warnings.Add($"{label} {folder}: the description has {description.Length} characters; agents may shorten or drop it above {MaxDescriptionChars}.");
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
            }
        }

        private static void WarnOverlappingFolders(string scope, string projectRoot, string home, SkillsReport report) {
            var baseRoot = scope == ScopeProject ? projectRoot : home;
            if (string.IsNullOrWhiteSpace(baseRoot))
                return;
            foreach (var (client, project, user) in ClientReads) {
                var owners = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
                foreach (var parts in scope == ScopeProject ? project : user) {
                    var skillsDir = Path.Combine(new[] { Path.GetFullPath(baseRoot) }.Concat(parts).ToArray());
                    try {
                        AssertNoLink(Path.GetFullPath(baseRoot), skillsDir);
                    }
                    catch (PyRevitException) {
                        continue;
                    }
                    if (!Directory.Exists(skillsDir))
                        continue;
                    foreach (var directory in Directory.GetDirectories(skillsDir).Where(path => !IsLink(path) && ReadMarker(path) != null)) {
                        var name = Path.GetFileName(directory);
                        if (!owners.TryGetValue(name, out var folders))
                            owners[name] = folders = new List<string>();
                        folders.Add(skillsDir);
                    }
                }
                foreach (var entry in owners.Where(entry => entry.Value.Count > 1).OrderBy(entry => entry.Key, StringComparer.Ordinal))
                    report.Warnings.Add($"{client} reads '{entry.Key}' from {entry.Value.Count} folders ({string.Join(", ", entry.Value)}); keep one copy.");
            }
        }

        private static void AssertInside(string root, string path) {
            var boundary = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!(Path.GetFullPath(path) + Path.DirectorySeparatorChar).StartsWith(boundary, StringComparison.OrdinalIgnoreCase))
                throw new PyRevitException($"Refusing {path}: it is outside {root}.");
        }

        private static void AssertNoLink(string baseRoot, string path) {
            var boundary = Path.GetFullPath(baseRoot).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            for (var current = new DirectoryInfo(Path.GetFullPath(path)); current != null; current = current.Parent) {
                if (string.Equals(current.FullName.TrimEnd(Path.DirectorySeparatorChar), boundary, StringComparison.OrdinalIgnoreCase))
                    return;
                if (IsLink(current.FullName))
                    throw new PyRevitException($"Refusing {current.FullName}: it is a link (junction or symlink).");
            }
            throw new PyRevitException($"Refusing {path}: it is outside {baseRoot}.");
        }

        private static bool ContainsLink(string directory) {
            foreach (var entry in Directory.GetFileSystemEntries(directory)) {
                if (IsLink(entry))
                    return true;
                if (Directory.Exists(entry) && ContainsLink(entry))
                    return true;
            }
            return false;
        }

        private static bool IsLink(string path) {
            try {
                return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
            }
            catch (Exception ex) when (ex is FileNotFoundException || ex is DirectoryNotFoundException) {
                return false;
            }
        }
    }
}
