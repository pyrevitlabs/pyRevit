using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace pyRevitLabs.Common {

    /// <summary>
    /// Reads and writes the persistent Windows <c>PATH</c> environment variable at user or
    /// machine scope.
    /// </summary>
    /// <remarks>
    /// Every mutation here is idempotent: adding an entry that is already present is a no-op,
    /// which is what keeps installers from stacking duplicate <c>PATH</c> tokens on every
    /// upgrade. Appending leaves an entry behind every directory registered before it, so an
    /// installer that must win over an older copy of the same executable registers its
    /// directory first instead. The value is always read and written unexpanded and kept as
    /// <see cref="RegistryValueKind.ExpandString"/> so that <c>%VAR%</c> tokens in unrelated
    /// entries survive a round-trip.
    /// </remarks>
    public static class SystemPath {

        internal const char PathSeparator = ';';

        private const string PathValueName = "Path";
        private const string UserEnvironmentSubKey = "Environment";
        private const string MachineEnvironmentSubKey =
            @"SYSTEM\CurrentControlSet\Control\Session Manager\Environment";

        /// <summary>
        /// Splits a raw <c>PATH</c> value into its directory tokens, dropping empty entries
        /// produced by stray separators.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value. May be <c>null</c>.</param>
        /// <returns>The non-empty directory tokens, in the order they appear.</returns>
        public static IList<string> Tokenize(string path) {
            if (string.IsNullOrEmpty(path))
                return new List<string>();
            return path
                .Split(PathSeparator)
                .Select(t => t.Trim())
                .Where(t => t.Length > 0)
                .ToList();
        }

        /// <summary>
        /// Canonicalizes a directory token for comparison purposes by trimming surrounding
        /// whitespace and any trailing separator.
        /// </summary>
        /// <param name="entry">The directory token to normalize.</param>
        /// <returns>The comparable form of the token.</returns>
        public static string NormalizeToken(string entry) {
            if (string.IsNullOrEmpty(entry))
                return string.Empty;
            var normalized = entry.Trim();
            while (normalized.Length > 3 && normalized[normalized.Length - 1] == '\\')
                normalized = normalized.Substring(0, normalized.Length - 1);
            return normalized;
        }

        /// <summary>
        /// Tests whether a raw <c>PATH</c> value already contains a directory, ignoring case and
        /// trailing separators. A token that merely contains the directory as a substring, such
        /// as <c>C:\Tools\bin-old</c> against <c>C:\Tools\bin</c>, is not a match.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value to test.</param>
        /// <param name="entry">The directory to look for.</param>
        /// <returns><c>true</c> if the directory is present as a whole token.</returns>
        public static bool HasEntry(string path, string entry) {
            var normalizedEntry = NormalizeToken(entry);
            if (normalizedEntry.Length == 0)
                return false;
            return Tokenize(path)
                .Any(t => string.Equals(NormalizeToken(t), normalizedEntry,
                    StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Counts how many times a directory appears in a raw <c>PATH</c> value. Values above
        /// one mean the value accumulated duplicates.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value to test.</param>
        /// <param name="entry">The directory to look for.</param>
        /// <returns>The number of matching tokens.</returns>
        public static int CountEntry(string path, string entry) {
            var normalizedEntry = NormalizeToken(entry);
            if (normalizedEntry.Length == 0)
                return 0;
            return Tokenize(path)
                .Count(t => string.Equals(NormalizeToken(t), normalizedEntry,
                    StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Returns a raw <c>PATH</c> value with a directory appended, unless it is already
        /// present. The existing value is carried over byte for byte so that registering a
        /// directory never reformats entries pyRevit did not write.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value to extend.</param>
        /// <param name="entry">The directory to add.</param>
        /// <returns>
        /// The extended value, or <paramref name="path"/> unchanged when the directory is
        /// already present.
        /// </returns>
        public static string AddEntry(string path, string entry) {
            if (HasEntry(path, entry))
                return path;
            var separator = string.Empty;
            var existing = path == null ? string.Empty : path.TrimEnd(PathSeparator, ' ');
            if (existing.Length > 0)
                separator = PathSeparator.ToString();
            return existing + separator + NormalizeToken(entry);
        }

        /// <summary>
        /// Returns a raw <c>PATH</c> value with a directory as its first entry, so that
        /// executables in it win over same-named ones in every other directory of that value.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value to extend.</param>
        /// <param name="entry">The directory to put first.</param>
        /// <returns>
        /// The reordered value, or <paramref name="path"/> unchanged when the directory already
        /// is the first entry. A directory that is absent is put in front of the existing text,
        /// which is carried over as is. One that is present further back is moved, which
        /// re-serializes the list like <see cref="RemoveEntry"/> does.
        /// </returns>
        public static string PrependEntry(string path, string entry) {
            var normalizedEntry = NormalizeToken(entry);
            if (normalizedEntry.Length == 0)
                return path;
            var firstToken = Tokenize(path).FirstOrDefault();
            if (string.Equals(NormalizeToken(firstToken), normalizedEntry,
                    StringComparison.OrdinalIgnoreCase))
                return path;
            var remainder = HasEntry(path, entry)
                ? RemoveEntry(path, entry)
                : (path ?? string.Empty).TrimStart(PathSeparator, ' ');
            if (remainder.Length == 0)
                return normalizedEntry;
            return normalizedEntry + PathSeparator + remainder;
        }

        /// <summary>
        /// Lists the copies of a file that exist in the directories of raw <c>PATH</c> values, in
        /// the order of those values, which is the order Windows resolves a command in.
        /// </summary>
        /// <param name="pathValues">
        /// The raw <c>PATH</c> values, in resolution order. Each one is expanded before it is
        /// split, as Windows does, so a <c>%VAR%</c> entry whose value holds several
        /// <c>;</c>-separated directories contributes every one of them.
        /// </param>
        /// <param name="fileName">The file to look for, such as <c>pyrevit.exe</c>.</param>
        /// <param name="fileExists">Tests whether a full file path exists.</param>
        /// <returns>The full paths of the copies found, each reported once.</returns>
        internal static IList<string> FindFileInPathValues(IEnumerable<string> pathValues,
                                                           string fileName,
                                                           Func<string, bool> fileExists) {
            return pathValues
                .SelectMany(v => Tokenize(Environment.ExpandEnvironmentVariables(v ?? string.Empty)))
                .Select(e => ResolveFileInEntry(e, fileName))
                .Where(f => f != null && fileExists(f))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static string ResolveFileInEntry(string entry, string fileName) {
            var directory = NormalizeToken((entry ?? string.Empty).Trim('"'));
            if (directory.Length == 0 || directory.IndexOfAny(Path.GetInvalidPathChars()) >= 0)
                return null;
            return Path.Combine(directory, fileName);
        }

        /// <summary>
        /// Returns a raw <c>PATH</c> value with every occurrence of a directory removed.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value to reduce.</param>
        /// <param name="entry">The directory to remove.</param>
        /// <returns>
        /// The reduced value. Dropping a token re-serializes the list, so empty tokens left by
        /// doubled separators are cleaned up in the result.
        /// </returns>
        public static string RemoveEntry(string path, string entry) {
            var normalizedEntry = NormalizeToken(entry);
            var tokens = Tokenize(path)
                .Where(t => !string.Equals(NormalizeToken(t), normalizedEntry,
                    StringComparison.OrdinalIgnoreCase))
                .ToList();
            return string.Join(PathSeparator.ToString(), tokens);
        }

        /// <summary>
        /// Lists the directories in a raw <c>PATH</c> value that appear more than once.
        /// </summary>
        /// <param name="path">The raw <c>PATH</c> value to inspect.</param>
        /// <returns>The duplicated directories, each reported once.</returns>
        public static IList<string> GetDuplicateEntries(string path) {
            return Tokenize(path)
                .GroupBy(NormalizeToken, StringComparer.OrdinalIgnoreCase)
                .Where(g => g.Count() > 1)
                .Select(g => g.Key)
                .ToList();
        }

        /// <summary>
        /// Reads the directories currently registered in <c>PATH</c> at the given scope.
        /// </summary>
        /// <param name="scope">
        /// Either <see cref="EnvironmentVariableTarget.User"/> or
        /// <see cref="EnvironmentVariableTarget.Machine"/>.
        /// </param>
        /// <returns>The directory tokens, in the order they appear.</returns>
        /// <exception cref="ArgumentOutOfRangeException">
        /// Thrown when <paramref name="scope"/> is <see cref="EnvironmentVariableTarget.Process"/>,
        /// which has no persistent registry representation.
        /// </exception>
        public static IList<string> GetPathEntries(EnvironmentVariableTarget scope) {
            using (var key = OpenEnvironmentKey(scope, writable: false))
                return Tokenize(ReadRawPathValue(key));
        }

        /// <summary>
        /// Lists the directories currently registered in <c>PATH</c> at the given scope that
        /// appear more than once.
        /// </summary>
        /// <param name="scope">The <c>PATH</c> scope to inspect.</param>
        /// <returns>The duplicated directories, each reported once.</returns>
        public static IList<string> GetDuplicatePathEntries(EnvironmentVariableTarget scope) {
            using (var key = OpenEnvironmentKey(scope, writable: false))
                return GetDuplicateEntries(ReadRawPathValue(key));
        }

        /// <summary>
        /// Lists the copies of a file found in the directories of the persistent <c>PATH</c>, in
        /// the order a newly started process resolves a command: machine entries, then user
        /// entries.
        /// </summary>
        /// <param name="fileName">The file to look for, such as <c>pyrevit.exe</c>.</param>
        /// <returns>The full paths of the copies found. The first one is the one that runs.</returns>
        /// <remarks>
        /// This reads the registry, not the <c>PATH</c> of the current process, which is a
        /// snapshot taken before any change made by this or a parent process.
        /// </remarks>
        public static IList<string> FindFileOnPath(string fileName) {
            var pathValues = new[] { EnvironmentVariableTarget.Machine, EnvironmentVariableTarget.User }
                .Select(GetRawPathValue);
            return FindFileInPathValues(pathValues, fileName, File.Exists);
        }

        private static string GetRawPathValue(EnvironmentVariableTarget scope) {
            using (var key = OpenEnvironmentKey(scope, writable: false))
                return ReadRawPathValue(key);
        }

        /// <summary>
        /// Registers a directory in <c>PATH</c> at the given scope unless it is already there,
        /// then notifies running processes that the environment changed.
        /// </summary>
        /// <param name="scope">The <c>PATH</c> scope to write to.</param>
        /// <param name="entry">The directory to register.</param>
        /// <param name="first">
        /// <c>true</c> to make the directory the first entry of the scope, moving it there when
        /// it is registered further back. <c>false</c> appends it when missing and never moves
        /// it.
        /// </param>
        /// <returns><c>true</c> if the value was modified.</returns>
        /// <remarks>
        /// Callers run after the installer's own environment-change broadcast, so this method
        /// must broadcast on its own or newly started shells will not pick the value up.
        /// Being first in the user scope still leaves the directory behind every machine entry,
        /// because Windows puts the machine <c>PATH</c> in front of the user one.
        /// </remarks>
        public static bool EnsurePathEntry(EnvironmentVariableTarget scope, string entry,
                                           bool first = false) {
            using (var key = OpenEnvironmentKey(scope, writable: true)) {
                var currentValue = ReadRawPathValue(key);
                var updatedValue = first
                    ? PrependEntry(currentValue, entry)
                    : AddEntry(currentValue, entry);
                if (string.Equals(currentValue, updatedValue, StringComparison.Ordinal))
                    return false;
                WriteRawPathValue(key, updatedValue);
            }
            BroadcastEnvironmentChange();
            return true;
        }

        /// <summary>
        /// Removes every occurrence of a directory from <c>PATH</c> at the given scope, then
        /// notifies running processes that the environment changed.
        /// </summary>
        /// <param name="scope">The <c>PATH</c> scope to write to.</param>
        /// <param name="entry">The directory to remove.</param>
        /// <returns>The number of removed entries.</returns>
        /// <remarks>
        /// Unlike <see cref="EnsurePathEntry"/>, this re-serializes the whole value, so padding
        /// and empty tokens in the remaining entries are normalized away.
        /// </remarks>
        public static int RemovePathEntries(EnvironmentVariableTarget scope, string entry) {
            int removed;
            using (var key = OpenEnvironmentKey(scope, writable: true)) {
                var currentValue = ReadRawPathValue(key);
                removed = CountEntry(currentValue, entry);
                if (removed == 0)
                    return 0;
                WriteRawPathValue(key, RemoveEntry(currentValue, entry));
            }
            BroadcastEnvironmentChange();
            return removed;
        }

        /// <summary>
        /// Resolves a <c>PATH</c> scope name as accepted on the command line.
        /// </summary>
        /// <param name="scopeName">The scope name, <c>user</c> or <c>machine</c>.</param>
        /// <param name="scope">Receives the matching scope.</param>
        /// <returns><c>true</c> if the name is a known scope.</returns>
        public static bool TryParseScope(string scopeName, out EnvironmentVariableTarget scope) {
            if (string.Equals(scopeName, "user", StringComparison.OrdinalIgnoreCase)) {
                scope = EnvironmentVariableTarget.User;
                return true;
            }
            if (string.Equals(scopeName, "machine", StringComparison.OrdinalIgnoreCase)) {
                scope = EnvironmentVariableTarget.Machine;
                return true;
            }
            scope = EnvironmentVariableTarget.User;
            return false;
        }

        private static RegistryKey OpenEnvironmentKey(EnvironmentVariableTarget scope, bool writable) {
            RegistryKey key;
            switch (scope) {
                case EnvironmentVariableTarget.User:
                    key = Registry.CurrentUser.OpenSubKey(UserEnvironmentSubKey, writable);
                    break;
                case EnvironmentVariableTarget.Machine:
                    key = RegistryKey
                        .OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64)
                        .OpenSubKey(MachineEnvironmentSubKey, writable);
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(scope), scope,
                        "PATH can only be read from or written to the User and Machine scopes.");
            }
            return RequireEnvironmentKey(key, scope, writable);
        }

        /// <summary>
        /// Guards against the null that <c>OpenSubKey</c> returns instead of throwing when
        /// access is denied, so a denied read never passes for an empty PATH and a denied write
        /// never reaches <see cref="RegistryKey.SetValue"/>.
        /// </summary>
        internal static RegistryKey RequireEnvironmentKey(RegistryKey key,
                                                           EnvironmentVariableTarget scope,
                                                           bool writable) {
            if (key is null)
                throw new UnauthorizedAccessException(string.Format(
                    "Could not open the {0} PATH registry key{1}.", scope,
                    writable ? " (elevation may be required)" : string.Empty));
            return key;
        }

        internal static string ReadRawPathValue(RegistryKey key) {
            return key?.GetValue(PathValueName, null,
                RegistryValueOptions.DoNotExpandEnvironmentNames) as string;
        }

        internal static void WriteRawPathValue(RegistryKey key, string value) {
            key.SetValue(PathValueName, value, ResolveValueKind(key));
        }

        private static RegistryValueKind ResolveValueKind(RegistryKey key) {
            if (key.GetValueNames().Contains(PathValueName, StringComparer.OrdinalIgnoreCase))
                return key.GetValueKind(PathValueName) == RegistryValueKind.String
                    ? RegistryValueKind.String
                    : RegistryValueKind.ExpandString;
            return RegistryValueKind.ExpandString;
        }

        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, UIntPtr wParam,
            string lParam, uint flags, uint timeout, out UIntPtr result);

        private static void BroadcastEnvironmentChange() {
            const uint wmSettingChange = 0x001A;
            const uint smtoAbortIfHung = 0x0002;
            var hwndBroadcast = new IntPtr(0xffff);
            SendMessageTimeout(hwndBroadcast, wmSettingChange, UIntPtr.Zero, "Environment",
                smtoAbortIfHung, 5000, out _);
        }
    }
}
