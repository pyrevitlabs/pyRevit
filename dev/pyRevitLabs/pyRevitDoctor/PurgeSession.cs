using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security;

namespace pyRevitDoctor {
    /// <summary>
    /// The flags shared by the purge commands.
    /// </summary>
    public sealed class PurgeOptions {
        public bool DryRun { get; init; }
        public bool Force { get; init; }
        public bool KeepConfig { get; init; }
    }

    /// <summary>
    /// One run of a purge command: its options, its output and its tally of what happened to each item.
    /// </summary>
    /// <remarks>
    /// In a dry run nothing is changed, but items reported as deleted are remembered so later steps of the
    /// same run, such as the staleness check of <c>purge-installs</c> inside <c>purge-all</c>, see them as gone.
    /// </remarks>
    public sealed class PurgeSession {
        readonly List<string> dryRunRemovedPaths = new();
        bool needsAdmin;
        bool filesInUse;

        public PurgeSession(PurgeOptions options, TextWriter output) {
            Options = options;
            Output = output;
        }

        public PurgeOptions Options { get; }
        public TextWriter Output { get; }
        public int DeletedCount { get; private set; }
        public int SkippedCount { get; private set; }
        public int FailedCount { get; private set; }

        public bool Exists(string path) {
            var normalized = path.TrimEnd('\\', '/');
            var removedInDryRun = dryRunRemovedPaths.Any(removed =>
                normalized.Equals(removed, StringComparison.OrdinalIgnoreCase)
                || normalized.StartsWith(removed + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase));
            return !removedInDryRun && (File.Exists(normalized) || Directory.Exists(normalized));
        }

        public void ReportDeleted(string item, string removedPath = null) {
            DeletedCount++;
            Output.WriteLine($"{(Options.DryRun ? "Fake Deleted" : "Deleted")} {item}");
            if (Options.DryRun && removedPath != null)
                dryRunRemovedPaths.Add(removedPath.TrimEnd('\\', '/'));
        }

        public void ReportSkipped(string reason, string item) {
            SkippedCount++;
            Output.WriteLine($"Skipped ({reason}) {item}");
        }

        public void ReportFailed(string item, Exception exception) {
            FailedCount++;
            needsAdmin |= exception is UnauthorizedAccessException or SecurityException;
            filesInUse |= exception is IOException;
            Output.WriteLine($"Error Deleting {item} | {exception.Message}");
        }

        public void PrintSummary() {
            Output.WriteLine();
            Output.WriteLine($"Summary: {DeletedCount} deleted, {SkippedCount} skipped, {FailedCount} failed"
                + (Options.DryRun ? " (dry run, nothing was changed)" : string.Empty));
            if (needsAdmin)
                Output.WriteLine("Some items need elevated rights. Run this command as admin.");
            if (filesInUse)
                Output.WriteLine("Some files are in use. Close programs using pyRevit and run pyrevit-doctor.exe from a folder outside the pyRevit install folders.");
        }
    }
}
