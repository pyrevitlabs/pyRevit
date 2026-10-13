using System;
using System.Collections.Generic;
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
    /// upgrade. The value is always read and written unexpanded and kept as
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
        /// Registers a directory in <c>PATH</c> at the given scope unless it is already there,
        /// then notifies running processes that the environment changed.
        /// </summary>
        /// <param name="scope">The <c>PATH</c> scope to write to.</param>
        /// <param name="entry">The directory to register.</param>
        /// <returns><c>true</c> if the value was modified.</returns>
        /// <remarks>
        /// Callers run after the installer's own environment-change broadcast, so this method
        /// must broadcast on its own or newly started shells will not pick the value up.
        /// </remarks>
        public static bool EnsurePathEntry(EnvironmentVariableTarget scope, string entry) {
            using (var key = OpenEnvironmentKey(scope, writable: true)) {
                var currentValue = ReadRawPathValue(key);
                var updatedValue = AddEntry(currentValue, entry);
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
            switch (scope) {
                case EnvironmentVariableTarget.User:
                    return Registry.CurrentUser.OpenSubKey(UserEnvironmentSubKey, writable);
                case EnvironmentVariableTarget.Machine:
                    return RegistryKey
                        .OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64)
                        .OpenSubKey(MachineEnvironmentSubKey, writable);
                default:
                    throw new ArgumentOutOfRangeException(nameof(scope), scope,
                        "PATH can only be read from or written to the User and Machine scopes.");
            }
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
