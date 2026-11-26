using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

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
    /// <c>name</c> line), so an edit is told from the folder content alone. <c>InstalledName</c> is the
    /// folder the copy was written to; a marker found in a folder of another name was copied there.
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
    /// marker, the atomic copy, leftover cleanup and the link guards.
    /// </summary>
    /// <remarks>
    /// Invariants: nothing is written, replaced or deleted through a link (reparse point); a folder
    /// counts as pyRevit-owned only when its marker parses, names that very folder, and the folder content
    /// matches the marker digest (an ownership record checked against the content, not proof of origin); a
    /// copy is built beside its destination and moved into place; only leftovers older than
    /// <see cref="StaleTempAge"/> are cleaned, and only while holding the folder's <see cref="Lock"/>.
    /// </remarks>
    internal static class SkillFiles {
        internal const string SkillFile = "SKILL.md";
        internal const string TempPrefix = ".pyrevit-tmp-";
        internal const int MaxFileBytes = 128 * 1024;
        internal static readonly TimeSpan StaleTempAge = TimeSpan.FromMinutes(10);
        internal static readonly TimeSpan LockTimeout = TimeSpan.FromSeconds(30);
        private const string MarkerFile = ".pyrevit-skill.json";
        private const int MaxFilesPerSkill = 256;
        private const int MaxMarkerBytes = 4 * 1024;
        private static readonly Regex NamePattern = new Regex("^[a-z0-9][a-z0-9-]{0,63}\\z", RegexOptions.Compiled);
        private static readonly Regex TopLevelNameLine = new Regex("^name\\s*:", RegexOptions.Compiled | RegexOptions.IgnoreCase);

        internal static bool IsValidName(string name) {
            return name != null && NamePattern.IsMatch(name);
        }

        /// <summary>
        /// The one filter for failures a per-skill or per-folder step reports and survives.
        /// </summary>
        internal static bool IsRecoverable(Exception ex) {
            return ex is PyRevitException || ex is IOException || ex is UnauthorizedAccessException;
        }

        /// <summary>
        /// Removes control, line-separator and Unicode format (bidi) characters so a file name cannot
        /// rewrite what the console shows.
        /// </summary>
        internal static string Printable(string text) {
            if (text == null)
                return null;
            var clean = new StringBuilder(text.Length);
            foreach (var character in text) {
                var category = char.GetUnicodeCategory(character);
                if (!char.IsControl(character) && category != UnicodeCategory.Format && category != UnicodeCategory.LineSeparator && category != UnicodeCategory.ParagraphSeparator)
                    clean.Append(character);
            }
            return clean.ToString();
        }

        internal static ShippedSkill LoadShipped(string directory, string name) {
            var files = CollectFiles(directory);
            return new ShippedSkill { Name = name, Files = files, Digest = Digest(files) };
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

        private static string Digest(List<(string Relative, string Path)> files) {
            using (var sha256 = IncrementalHash.CreateHash(HashAlgorithmName.SHA256)) {
                foreach (var file in files) {
                    var bytes = File.ReadAllBytes(file.Path);
                    sha256.AppendData(Encoding.UTF8.GetBytes(file.Relative));
                    sha256.AppendData(new byte[] { 0 });
                    sha256.AppendData(BitConverter.GetBytes((long)bytes.Length));
                    sha256.AppendData(bytes);
                }
                return Hex(sha256.GetHashAndReset());
            }
        }

        private static string Hex(byte[] bytes) {
            return BitConverter.ToString(bytes).Replace("-", string.Empty).ToLowerInvariant();
        }

        private static byte[] ReadFile((string Relative, string Path) file, string renameTo) {
            var bytes = File.ReadAllBytes(file.Path);
            return renameTo != null && file.Relative == SkillFile ? RenameSkill(bytes, renameTo) : bytes;
        }

        /// <summary>
        /// Rewrites the top-level <c>name</c> line of the front matter, whatever its quoting or spacing,
        /// keeping the BOM, the line endings and every other byte.
        /// </summary>
        /// <exception cref="PyRevitException">The file has no closed front matter block.</exception>
        private static byte[] RenameSkill(byte[] bytes, string name) {
            var encoding = new UTF8Encoding(false);
            var lines = encoding.GetString(bytes).Split('\n').ToList();
            if (lines[0].TrimStart('﻿').Trim() != "---")
                throw new PyRevitException($"SKILL.md has no front matter, so its name cannot be rewritten to '{name}'.");
            var lineEnd = lines[0].EndsWith("\r") ? "\r" : string.Empty;
            for (var index = 1; index < lines.Count; index++) {
                if (lines[index].Trim() == "---") {
                    lines.Insert(1, "name: " + name + lineEnd);
                    return encoding.GetBytes(string.Join("\n", lines));
                }
                if (TopLevelNameLine.IsMatch(lines[index])) {
                    lines[index] = "name: " + name + (lines[index].EndsWith("\r") ? "\r" : string.Empty);
                    return encoding.GetBytes(string.Join("\n", lines));
                }
            }
            throw new PyRevitException($"SKILL.md front matter is never closed, so its name cannot be rewritten to '{name}'.");
        }

        private static SkillMarker ReadMarker(string folder) {
            var path = Path.Combine(folder, MarkerFile);
            try {
                if (!File.Exists(path) || IsLink(path) || new FileInfo(path).Length > MaxMarkerBytes)
                    return null;
                var json = JToken.Parse(File.ReadAllText(path)) as JObject;
                var source = Text(json, "source");
                var sha256 = Text(json, "sha256");
                var installedName = Text(json, "installedName");
                if (source != PyRevitAgentSkills.ShippedSource || sha256 == null || installedName == null)
                    return null;
                return new SkillMarker {
                    Name = Text(json, "name"),
                    InstalledName = installedName,
                    Sha256 = sha256,
                    InstalledSha256 = Text(json, "installedSha256") ?? sha256,
                };
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException || ex is pyRevitLabs.Json.JsonException || ex is InvalidCastException || ex is FormatException) {
                return null;
            }
        }

        private static SkillMarker ReadOwnMarker(string folder) {
            var marker = ReadMarker(folder);
            return marker != null && string.Equals(marker.InstalledName, Path.GetFileName(folder), StringComparison.OrdinalIgnoreCase) ? marker : null;
        }

        private static string Text(JObject json, string key) {
            return json != null && json.TryGetValue(key, out var token) && token.Type == JTokenType.String ? (string)token : null;
        }

        /// <summary>
        /// Reads the marker of <paramref name="folder"/> and checks the folder content against it.
        /// </summary>
        /// <remarks>
        /// A link, a plain file, a folder without a valid marker or one whose marker names another folder
        /// (a copy) has no <c>Marker</c>. An owned folder is <c>Intact</c> only when it holds exactly the marker
        /// and the markdown files the marker digest covers; anything else is listed in <c>Extras</c> or
        /// explained in <c>Note</c>.
        /// </remarks>
        internal static OwnedCheck Verify(string folder) {
            return Check(folder, ReadOwnMarker);
        }

        private static OwnedCheck Check(string folder, Func<string, SkillMarker> readMarker) {
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
            check.Marker = readMarker(folder);
            if (check.Marker == null)
                return check;
            try {
                var files = CollectFiles(folder);
                check.Extras.AddRange(Extras(folder, folder, new HashSet<string>(files.Select(file => file.Relative), StringComparer.Ordinal)));
                check.Intact = check.Extras.Count == 0 && Digest(files) == check.Marker.InstalledSha256;
            }
            catch (Exception ex) when (IsRecoverable(ex)) {
                check.Note = ex.Message;
            }
            return check;
        }

        private static IEnumerable<string> Extras(string root, string directory, HashSet<string> collected) {
            foreach (var entry in Directory.GetFileSystemEntries(directory)) {
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

        /// <summary>
        /// Lists the pyRevit-owned skill folders in <paramref name="skillsDir"/>, keyed by shipped skill name.
        /// </summary>
        /// <remarks>
        /// Empty when the skills folder is missing or a link lies on the way to it.
        /// </remarks>
        internal static List<(string Directory, string Key)> FindOwnedFolders(string baseRoot, string skillsDir) {
            var found = new List<(string Directory, string Key)>();
            try {
                AssertNoLink(baseRoot, skillsDir);
                if (!Directory.Exists(skillsDir))
                    return found;
                foreach (var directory in Directory.GetDirectories(skillsDir).Where(path => !IsLink(path))) {
                    var marker = ReadOwnMarker(directory);
                    if (marker != null)
                        found.Add((directory, marker.Name ?? Path.GetFileName(directory)));
                }
            }
            catch (Exception ex) when (IsRecoverable(ex)) {
                return new List<(string Directory, string Key)>();
            }
            return found;
        }

        /// <summary>
        /// Checks that <paramref name="skillsDir"/> is inside <paramref name="baseRoot"/> with no link on the
        /// way, and creates it when <paramref name="create"/>.
        /// </summary>
        /// <returns>Whether the skills folder exists afterwards.</returns>
        internal static bool EnsureSkillsDir(string baseRoot, string skillsDir, bool create) {
            AssertInside(baseRoot, skillsDir);
            AssertNoLink(baseRoot, skillsDir);
            if (Directory.Exists(skillsDir))
                return true;
            if (create)
                Directory.CreateDirectory(skillsDir);
            return create;
        }

        /// <summary>
        /// Writes <paramref name="skill"/> to <c>skillsDir/installedName</c> through a temporary folder.
        /// </summary>
        /// <returns>A warning when the replaced copy could not be deleted, otherwise null.</returns>
        /// <remarks>
        /// On failure the previous copy, if any, is still in place and the temporary folder is removed.
        /// </remarks>
        internal static string WriteAtomically(string skillsDir, ShippedSkill skill, string installedName, bool replace) {
            if (!IsValidName(installedName))
                throw new PyRevitException($"'{installedName}' is not a valid skill folder name.");
            var destination = Path.Combine(skillsDir, installedName);
            AssertInside(skillsDir, destination);
            var temp = Path.Combine(skillsDir, TempPrefix + Guid.NewGuid().ToString("N"));
            try {
                Stage(temp, skill, installedName);
                return SwapIn(temp, destination, skillsDir, replace);
            }
            finally {
                if (Directory.Exists(temp) && !IsLink(temp))
                    Directory.Delete(temp, recursive: true);
            }
        }

        private static void Stage(string temp, ShippedSkill skill, string installedName) {
            Directory.CreateDirectory(temp);
            var renameTo = installedName == skill.Name ? null : installedName;
            foreach (var file in skill.Files) {
                var target = Path.Combine(temp, file.Relative.Replace('/', Path.DirectorySeparatorChar));
                Directory.CreateDirectory(Path.GetDirectoryName(target));
                File.WriteAllBytes(target, ReadFile(file, renameTo));
            }
            WriteMarker(temp, skill, installedName, Digest(CollectFiles(temp)));
        }

        private static string SwapIn(string temp, string destination, string skillsDir, bool replace) {
            if (!replace) {
                Directory.Move(temp, destination);
                return null;
            }
            if (ContainsLink(destination))
                throw new PyRevitException($"Refusing to replace {destination}: it contains a link or a cloud placeholder.");
            var aside = Path.Combine(skillsDir, TempPrefix + Guid.NewGuid().ToString("N"));
            Directory.Move(destination, aside);
            TryTouch(aside);
            try {
                Directory.Move(temp, destination);
            }
            catch (Exception ex) {
                PutBack(aside, destination, ex);
                throw;
            }
            return TryDelete(aside);
        }

        private static void PutBack(string aside, string destination, Exception cause) {
            try {
                Directory.Move(aside, destination);
            }
            catch (Exception restoreError) {
                throw new IOException($"{cause.Message} The old copy could not be put back and is in {aside}: {restoreError.Message}", cause);
            }
        }

        private static void TryTouch(string directory) {
            try {
                Directory.SetLastWriteTimeUtc(directory, DateTime.UtcNow);
            }
            catch (Exception ex) when (IsRecoverable(ex)) {
                return;
            }
        }

        private static string TryDelete(string directory) {
            try {
                Directory.Delete(directory, recursive: true);
                return null;
            }
            catch (Exception ex) when (IsRecoverable(ex)) {
                return $"Could not remove the old copy {directory}: {ex.Message}";
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
        /// Moves a verified leftover back to its destination when that destination is missing, so an
        /// interrupted replace does not lose the only copy.
        /// </param>
        /// <returns>The warnings for leftovers that were restored, kept or could not be cleaned.</returns>
        /// <remarks>
        /// Only folders older than <see cref="StaleTempAge"/> are touched, so a run in progress is left alone.
        /// A leftover is restored or deleted only when its marker is valid and its content matches the marker
        /// digest; its recorded name must be a valid skill name. An old leftover without a marker (a copy killed before the
        /// marker was written) is deleted when it holds only markdown files and folders. Anything else is kept
        /// with a warning. Links, and folders that contain one, are never followed.
        /// </remarks>
        internal static List<string> SweepTemp(string skillsDir, bool restore) {
            var warnings = new List<string>();
            foreach (var directory in Directory.GetDirectories(skillsDir, TempPrefix + "*").OrderBy(path => path, StringComparer.Ordinal)) {
                try {
                    if (IsLink(directory) || Directory.GetLastWriteTimeUtc(directory) > DateTime.UtcNow - StaleTempAge)
                        continue;
                    if (!Directory.EnumerateFileSystemEntries(directory).Any()) {
                        Directory.Delete(directory);
                        continue;
                    }
                    if (ContainsLink(directory)) {
                        warnings.Add($"Kept {directory}: it is a leftover of an interrupted run but it contains a link.");
                        continue;
                    }
                    var check = Check(directory, ReadMarker);
                    if (check.Marker == null) {
                        if (IsPartialCopy(directory))
                            Directory.Delete(directory, recursive: true);
                        else
                            warnings.Add($"Kept {directory}: it is a leftover of an interrupted run but holds files other than markdown.");
                        continue;
                    }
                    if (!check.Intact) {
                        warnings.Add($"Kept {directory}: it is a leftover of an interrupted run but its content does not match its marker.");
                        continue;
                    }
                    var destination = IsValidName(check.Marker.InstalledName) ? Path.Combine(skillsDir, check.Marker.InstalledName) : null;
                    if (restore && destination != null && !IsLink(destination) && !File.Exists(destination) && !Directory.Exists(destination)) {
                        Directory.Move(directory, destination);
                        warnings.Add($"Restored {destination} from {directory}, left by an interrupted run.");
                    }
                    else
                        Directory.Delete(directory, recursive: true);
                }
                catch (Exception ex) when (IsRecoverable(ex)) {
                    warnings.Add($"Could not clean up {directory}: {ex.Message}");
                }
            }
            return warnings;
        }

        private static bool IsPartialCopy(string directory) {
            return Directory.GetFiles(directory).All(file => file.EndsWith(".md", StringComparison.OrdinalIgnoreCase))
                && Directory.GetDirectories(directory).All(IsPartialCopy);
        }

        /// <summary>
        /// Takes a named mutex for <paramref name="skillsDir"/>, so two pyRevit commands do not work in one skills
        /// folder at the same time.
        /// </summary>
        /// <exception cref="PyRevitException">The mutex was not free within <see cref="LockTimeout"/>.</exception>
        internal static IDisposable Lock(string skillsDir) {
            var key = Hex(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(skillsDir).ToLowerInvariant()))).Substring(0, 16);
            var mutex = new Mutex(false, "Local\\pyrevit-skills-" + key);
            bool acquired;
            try {
                acquired = mutex.WaitOne(LockTimeout);
            }
            catch (AbandonedMutexException) {
                acquired = true;
            }
            if (!acquired) {
                mutex.Dispose();
                throw new PyRevitException($"Another pyRevit command is working in {skillsDir}. Try again when it has finished.");
            }
            return new SkillsLock(mutex);
        }

        private sealed class SkillsLock : IDisposable {
            private readonly Mutex mutex;

            public SkillsLock(Mutex mutex) {
                this.mutex = mutex;
            }

            public void Dispose() {
                mutex.ReleaseMutex();
                mutex.Dispose();
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
                    throw new PyRevitException($"Refusing {current.FullName}: it is a link (junction or symlink) on the way to the skills folder.");
            }
            throw new PyRevitException($"Refusing {path}: it is outside {baseRoot}.");
        }

        internal static bool ContainsLink(string directory) {
            foreach (var entry in Directory.GetFileSystemEntries(directory)) {
                if (IsLink(entry))
                    return true;
                if (Directory.Exists(entry) && ContainsLink(entry))
                    return true;
            }
            return false;
        }

        internal static bool IsLink(string path) {
            try {
                return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
            }
            catch (Exception ex) when (ex is FileNotFoundException || ex is DirectoryNotFoundException) {
                return false;
            }
        }
    }
}
