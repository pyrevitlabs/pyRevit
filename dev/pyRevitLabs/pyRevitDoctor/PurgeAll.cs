using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;

namespace pyRevitDoctor {
    /// <summary>
    /// <c>purge-all</c>: unregisters the MCP integrations, then runs <see cref="PurgeFiles"/> and <see cref="PurgeInstalls"/>.
    /// </summary>
    /// <remarks>
    /// Invariant: the files go before the registry records, so the <c>_is1</c> entries of the removed
    /// installs are stale by the time <see cref="PurgeInstalls"/> checks them. The MCP step has to run
    /// first because it needs a working <c>pyrevit.exe</c>, and it runs once per distinct executable
    /// because <c>--owned</c> only removes the registrations of the executable that runs it. When
    /// <see cref="PurgeFiles"/> aborts, the registry is left alone, and when a timed-out <c>pyrevit.exe</c> cannot
    /// be stopped nothing is purged.
    /// </remarks>
    public static class PurgeAll {
        const string McpUninstallArguments = "mcp uninstall --all --owned";
        const int McpUninstallTimeoutMilliseconds = 60_000;

        public static void Run(PurgeSession session, MachineLocations locations) {
            if (!UninstallMcpIntegrations(session, locations))
                return;
            if (PurgeFiles.Run(session, locations))
                PurgeInstalls.Run(session);
        }

        static bool UninstallMcpIntegrations(PurgeSession session, MachineLocations locations) {
            var executables = FindPyRevitExecutables(session, locations);
            if (executables.Count == 0)
                session.ReportSkipped("pyrevit.exe not found", $"MCP client registrations (pyrevit {McpUninstallArguments})");
            return executables.All(pyrevitExe => UninstallMcpIntegrations(session, pyrevitExe));
        }

        static bool UninstallMcpIntegrations(PurgeSession session, string pyrevitExe) {
            var item = $"MCP client registrations of {pyrevitExe} (pyrevit {McpUninstallArguments})";
            if (session.Options.DryRun) {
                session.ReportDeleted(item);
                return true;
            }

            Process process;
            try {
                process = Process.Start(new ProcessStartInfo(pyrevitExe, McpUninstallArguments) { UseShellExecute = false });
            }
            catch (Exception ex) {
                session.ReportFailed(item, ex);
                return true;
            }

            using (process) {
                if (!process.WaitForExit(McpUninstallTimeoutMilliseconds))
                    return StopTimedOutProcess(session, process, item);
                if (process.ExitCode != 0)
                    session.ReportFailed(item, new InvalidOperationException($"pyrevit.exe exited with code {process.ExitCode}."));
                else
                    session.ReportDeleted(item);
                return true;
            }
        }

        static bool StopTimedOutProcess(PurgeSession session, Process process, string item) {
            try {
                process.Kill(entireProcessTree: true);
                process.WaitForExit();
            }
            catch (Exception ex) {
                session.ReportFailed($"{item}, the process could not be stopped, so nothing else was purged", ex);
                return false;
            }
            session.ReportFailed(item, new TimeoutException($"pyrevit.exe did not finish within {McpUninstallTimeoutMilliseconds / 1000} seconds and was stopped."));
            return true;
        }

        static IReadOnlyList<string> FindPyRevitExecutables(PurgeSession session, MachineLocations locations) {
            var candidates = new[] { Path.Combine(AppContext.BaseDirectory, "pyrevit.exe") }
                .Concat(PurgeTargets.InstallDirectories(locations).Select(directory => Path.Combine(directory, "bin", "pyrevit.exe")));
            return candidates
                .Select(Path.GetFullPath)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Where(session.Exists)
                .ToList();
        }
    }
}
