using System;
using System.Collections.Generic;
using System.IO;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Deletes agent run records and <c>capture_view</c> images last written before a cutoff.
    /// </summary>
    /// <remarks>
    /// Each run folder and capture is deleted on its own, so one that can't be deleted, such
    /// as an exported PDF the user has open, stays for a later prune while the rest are removed.
    /// A run folder that fails part way may lose some files before the failure.
    /// </remarks>
    internal static class AgentRecordPruner {
        /// <summary>
        /// Returns how many run folders and captures were removed. A missing folder prunes
        /// nothing; each entry that couldn't be removed adds a message to
        /// <paramref name="failures"/>.
        /// </summary>
        public static int Prune(string runsDir, string capturesDir, DateTime cutoff, ICollection<string> failures) {
            var removed = 0;
            foreach (var runDir in ListEntries(runsDir, Directory.GetDirectories, failures)) {
                if (TryDelete(runDir, Directory.GetLastWriteTime, path => Directory.Delete(path, recursive: true), cutoff, failures))
                    removed++;
            }
            foreach (var capture in ListEntries(capturesDir, Directory.GetFiles, failures)) {
                if (TryDelete(capture, File.GetLastWriteTime, File.Delete, cutoff, failures))
                    removed++;
            }
            return removed;
        }

        private static string[] ListEntries(string folder, Func<string, string[]> list, ICollection<string> failures) {
            try {
                return Directory.Exists(folder) ? list(folder) : new string[0];
            }
            catch (Exception ex) {
                failures.Add($"Could not list '{folder}': {ex.Message}");
                return new string[0];
            }
        }

        private static bool TryDelete(
            string path, Func<string, DateTime> lastWrite, Action<string> delete, DateTime cutoff, ICollection<string> failures) {
            try {
                if (lastWrite(path) >= cutoff)
                    return false;
                delete(path);
                return true;
            }
            catch (Exception ex) {
                failures.Add($"Could not delete '{path}': {ex.Message}");
                return false;
            }
        }
    }
}
