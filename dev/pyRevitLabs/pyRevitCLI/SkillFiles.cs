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
    /// A shipped skill as the installer sees it: its markdown files and their digest.
    /// </summary>
    internal sealed class ShippedSkill {
        public string Name { get; set; }
        public List<(string Relative, string Path)> Files { get; set; }
        public string Digest { get; set; }
    }

    /// <summary>
    /// The ownership record <c>.pyrevit-skill.json</c> in an installed skill folder.
    /// </summary>
    /// <remarks>
    /// <c>Sha256</c> is the digest of the shipped skill, so <c>status</c> can tell a stale copy.
    /// <c>InstalledSha256</c> is the digest of the files as written (a prefixed copy has a different
    /// <c>name</c> line), so an edit is told from the folder content alone.
    /// </remarks>
    internal sealed class SkillMarker {
        public string Name { get; set; }
        public string InstalledName { get; set; }
        public string Sha256 { get; set; }
        public string InstalledSha256 { get; set; }
    }

    /// <summary>
    /// What is in a folder that might be an installed skill.
    /// </summary>
    internal sealed class OwnedCheck {
        public bool Exists { get; set; }
        public SkillMarker Marker { get; set; }
        public bool Intact { get; set; }
        public List<string> Extras { get; } = new List<string>();
        public string Note { get; set; }
    }

    /// <summary>
    /// File-level work of the skill installer: collecting and digesting skill files, the ownership
    /// marker, the atomic copy and the link guards.
    /// </summary>
    /// <remarks>
    /// Invariants: nothing is written, replaced or deleted through a link (reparse point); a folder
    /// counts as pyRevit-owned only when its marker parses and the folder content matches the marker
    /// digest, which is an ownership record checked against the content, not proof of origin; a copy is
    /// built beside its destination and moved into place.
    /// </remarks>
    internal static class SkillFiles {
        public const string MarkerFile = ".pyrevit-skill.json";
        public const string SkillFile = "SKILL.md";
        public const string TempPrefix = ".pyrevit-tmp-";
        public const int MaxFileBytes = 128 * 1024;
        public const int MaxFilesPerSkill = 256;
        private const int MaxMarkerBytes = 4 * 1024;
        private static readonly Regex NamePattern = new Regex("^[a-z0-9][a-z0-9-]{0,63}\\z", RegexOptions.Compiled);
        private static readonly Regex NameLine = new Regex("^\\s*name\\s*:", RegexOptions.Compiled | RegexOptions.IgnoreCase);

        public static bool IsValidName(string name) {
            return name != null && NamePattern.IsMatch(name);
        }

        public static List<(string Relative, string Path)> CollectFiles(string root) {
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

        public static string Digest(List<(string Relative, string Path)> files, string renameTo = null) {
            using (var sha256 = IncrementalHash.CreateHash(HashAlgorithmName.SHA256)) {
                foreach (var file in files) {
                    var bytes = ReadFile(file, renameTo);
                    sha256.AppendData(Encoding.UTF8.GetBytes(file.Relative));
                    sha256.AppendData(new byte[] { 0 });
                    sha256.AppendData(BitConverter.GetBytes((long)bytes.Length));
                    sha256.AppendData(bytes);
                }
                return BitConverter.ToString(sha256.GetHashAndReset()).Replace("-", string.Empty).ToLowerInvariant();
            }
        }

        public static byte[] ReadFile((string Relative, string Path) file, string renameTo) {
            var bytes = File.ReadAllBytes(file.Path);
            return renameTo != null && file.Relative == SkillFile ? RenameSkill(bytes, renameTo) : bytes;
        }

        /// <summary>
        /// Rewrites the <c>name</c> front matter line, whatever its quoting or spacing, keeping the
        /// BOM, the line endings and every other byte.
        /// </summary>
        public static byte[] RenameSkill(byte[] bytes, string name) {
            var encoding = new UTF8Encoding(false);
            var lines = encoding.GetString(bytes).Split('\n').ToList();
            var lineEnd = lines[0].EndsWith("\r") ? "\r" : string.Empty;
            for (var index = 1; index < lines.Count && lines[index].Trim() != "---"; index++) {
                if (NameLine.IsMatch(lines[index])) {
                    lines[index] = "name: " + name + (lines[index].EndsWith("\r") ? "\r" : string.Empty);
                    return encoding.GetBytes(string.Join("\n", lines));
                }
            }
            lines.Insert(1, "name: " + name + lineEnd);
            return encoding.GetBytes(string.Join("\n", lines));
        }

        public static SkillMarker ReadMarker(string folder) {
            var path = Path.Combine(folder, MarkerFile);
            try {
                if (!File.Exists(path) || IsLink(path) || new FileInfo(path).Length > MaxMarkerBytes)
                    return null;
                var json = JToken.Parse(File.ReadAllText(path)) as JObject;
                var source = Text(json, "source");
                var sha256 = Text(json, "sha256");
                if (source != PyRevitAgentSkills.ShippedSource || sha256 == null)
                    return null;
                return new SkillMarker {
                    Name = Text(json, "name"),
                    InstalledName = Text(json, "installedName"),
                    Sha256 = sha256,
                    InstalledSha256 = Text(json, "installedSha256") ?? sha256,
                };
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException || ex is pyRevitLabs.Json.JsonException || ex is InvalidCastException || ex is FormatException) {
                return null;
            }
        }

        private static string Text(JObject json, string key) {
            return json != null && json.TryGetValue(key, out var token) && token.Type == JTokenType.String ? (string)token : null;
        }

        /// <summary>
        /// Reads the marker of <paramref name="folder"/> and checks the folder content against it.
        /// </summary>
        /// <remarks>
        /// A link, a plain file or a folder without a valid marker has no <c>Marker</c>. An owned folder is
        /// <c>Intact</c> only when it holds exactly the marker and the markdown files the marker digest
        /// covers; anything else is listed in <c>Extras</c> or explained in <c>Note</c>.
        /// </remarks>
        public static OwnedCheck Verify(string folder) {
            var check = new OwnedCheck();
            if (IsLink(folder)) {
                check.Exists = true;
                check.Note = "is a link or a cloud placeholder (reparse point), skipped";
                return check;
            }
            if (File.Exists(folder)) {
                check.Exists = true;
                check.Note = "is a file, not a folder, skipped";
                return check;
            }
            if (!Directory.Exists(folder))
                return check;
            check.Exists = true;
            check.Marker = ReadMarker(folder);
            if (check.Marker == null)
                return check;
            try {
                var files = CollectFiles(folder);
                check.Extras.AddRange(Extras(folder, folder, new HashSet<string>(files.Select(file => file.Relative), StringComparer.Ordinal)));
                check.Intact = check.Extras.Count == 0 && Digest(files) == check.Marker.InstalledSha256;
            }
            catch (Exception ex) when (ex is PyRevitException || ex is IOException || ex is UnauthorizedAccessException) {
                check.Note = ex.Message;
            }
            return check;
        }

        private static IEnumerable<string> Extras(string root, string directory, HashSet<string> collected) {
            var entries = Directory.GetFileSystemEntries(directory);
            foreach (var entry in entries) {
                var relative = Path.GetRelativePath(root, entry).Replace('\\', '/');
                if (IsLink(entry))
                    yield return relative + " (link)";
                else if (Directory.Exists(entry)) {
                    var inner = Extras(root, entry, collected).ToList();
                    if (inner.Count == 0 && !collected.Any(file => file.StartsWith(relative + "/", StringComparison.Ordinal)))
                        yield return relative + "/";
                    foreach (var item in inner)
                        yield return item;
                }
                else if (!collected.Contains(relative) && !(directory == root && relative == MarkerFile))
                    yield return relative;
            }
        }

        public static void WriteAtomically(string skillsDir, ShippedSkill skill, string installedName, bool replace, List<string> warnings) {
            if (!IsValidName(installedName))
                throw new PyRevitException($"'{installedName}' is not a valid skill folder name.");
            var destination = Path.Combine(skillsDir, installedName);
            AssertInside(skillsDir, destination);
            var temp = Path.Combine(skillsDir, TempPrefix + Guid.NewGuid().ToString("N"));
            try {
                Directory.CreateDirectory(temp);
                var renameTo = installedName == skill.Name ? null : installedName;
                foreach (var file in skill.Files) {
                    var target = Path.Combine(temp, file.Relative.Replace('/', Path.DirectorySeparatorChar));
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    File.WriteAllBytes(target, ReadFile(file, renameTo));
                }
                WriteMarker(temp, skill, installedName, Digest(CollectFiles(temp)));

                if (!replace) {
                    Directory.Move(temp, destination);
                    return;
                }
                if (ContainsLink(destination))
                    throw new PyRevitException($"Refusing to replace {destination}: it contains a link or a cloud placeholder.");
                var aside = Path.Combine(skillsDir, TempPrefix + Guid.NewGuid().ToString("N"));
                Directory.Move(destination, aside);
                try {
                    Directory.Move(temp, destination);
                }
                catch (Exception ex) {
                    try {
                        Directory.Move(aside, destination);
                    }
                    catch (Exception restoreError) {
                        throw new IOException($"{ex.Message} The old copy could not be put back and is in {aside}: {restoreError.Message}", ex);
                    }
                    throw;
                }
                try {
                    Directory.Delete(aside, recursive: true);
                }
                catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
                    warnings.Add($"Could not remove the old copy {aside}: {ex.Message}");
                }
            }
            finally {
                if (Directory.Exists(temp) && !IsLink(temp))
                    Directory.Delete(temp, recursive: true);
            }
        }

        private static void WriteMarker(string folder, ShippedSkill skill, string installedName, string installedDigest) {
            var marker = new JObject { ["source"] = PyRevitAgentSkills.ShippedSource };
            var version = CurrentVersion();
            if (version != null)
                marker["version"] = version;
            marker["name"] = skill.Name;
            marker["installedName"] = installedName;
            marker["sha256"] = skill.Digest;
            marker["installedSha256"] = installedDigest;
            File.WriteAllText(Path.Combine(folder, MarkerFile), marker.ToString());
        }

        private static string CurrentVersion() {
            var version = typeof(SkillFiles).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion;
            if (string.IsNullOrWhiteSpace(version))
                return null;
            var plus = version.IndexOf('+');
            return plus > 0 ? version.Substring(0, plus) : version;
        }

        /// <summary>
        /// Cleans up <c>.pyrevit-tmp-*</c> folders a crashed run left in <paramref name="skillsDir"/>.
        /// </summary>
        /// <param name="restore">
        /// Moves a leftover that carries a marker back to its destination when that destination is
        /// missing, so an interrupted replace does not lose the only copy.
        /// </param>
        /// <remarks>
        /// Removes only empty folders and folders with a valid marker; never a link and never a folder
        /// that contains one.
        /// </remarks>
        public static void SweepTemp(string skillsDir, bool restore, List<string> warnings) {
            foreach (var directory in Directory.GetDirectories(skillsDir, TempPrefix + "*").OrderBy(path => path, StringComparer.Ordinal)) {
                try {
                    if (IsLink(directory))
                        continue;
                    if (!Directory.EnumerateFileSystemEntries(directory).Any()) {
                        Directory.Delete(directory);
                        continue;
                    }
                    var marker = ReadMarker(directory);
                    if (marker == null || ContainsLink(directory))
                        continue;
                    var destination = marker.InstalledName != null && IsValidName(marker.InstalledName) ? Path.Combine(skillsDir, marker.InstalledName) : null;
                    if (restore && destination != null && !IsLink(destination) && !File.Exists(destination) && !Directory.Exists(destination)) {
                        Directory.Move(directory, destination);
                        warnings.Add($"Restored {destination} from {directory}, left by an interrupted run.");
                    }
                    else
                        Directory.Delete(directory, recursive: true);
                }
                catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
                    warnings.Add($"Could not clean up {directory}: {ex.Message}");
                }
            }
        }

        public static void AssertInside(string root, string path) {
            var boundary = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!(Path.GetFullPath(path) + Path.DirectorySeparatorChar).StartsWith(boundary, StringComparison.OrdinalIgnoreCase))
                throw new PyRevitException($"Refusing {path}: it is outside {root}.");
        }

        public static void AssertNoLink(string baseRoot, string path) {
            var boundary = Path.GetFullPath(baseRoot).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            for (var current = new DirectoryInfo(Path.GetFullPath(path)); current != null; current = current.Parent) {
                if (string.Equals(current.FullName.TrimEnd(Path.DirectorySeparatorChar), boundary, StringComparison.OrdinalIgnoreCase))
                    return;
                if (IsLink(current.FullName))
                    throw new PyRevitException($"Refusing {current.FullName}: it is a link (junction or symlink) on the way to the skills folder.");
            }
            throw new PyRevitException($"Refusing {path}: it is outside {baseRoot}.");
        }

        public static bool ContainsLink(string directory) {
            foreach (var entry in Directory.GetFileSystemEntries(directory)) {
                if (IsLink(entry))
                    return true;
                if (Directory.Exists(entry) && ContainsLink(entry))
                    return true;
            }
            return false;
        }

        public static bool IsLink(string path) {
            try {
                return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
            }
            catch (Exception ex) when (ex is FileNotFoundException || ex is DirectoryNotFoundException) {
                return false;
            }
        }
    }
}
