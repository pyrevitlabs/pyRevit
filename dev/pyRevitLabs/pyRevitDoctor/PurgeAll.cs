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
    /// <see cref="PurgeFiles"/> aborts, the registry is left alone.
    /// </remarks>
    public static class PurgeAll {
        const string McpUninstallArguments = "mcp uninstall --all --owned";
        const int McpUninstallTimeoutMilliseconds = 60_000;

        public static void Run(PurgeSession session, MachineLocations locations) {
            UninstallMcpIntegrations(session, locations);
            if (PurgeFiles.Run(session, locations))
                PurgeInstalls.Run(session);
        }

        static void UninstallMcpIntegrations(PurgeSession session, MachineLocations locations) {
            var executables = FindPyRevitExecutables(session, locations);
            if (executables.Count == 0)
                session.ReportSkipped("pyrevit.exe not found", $"MCP client registrations (pyrevit {McpUninstallArguments})");
            foreach (var pyrevitExe in executables)
                UninstallMcpIntegrations(session, pyrevitExe);
        }

        static void UninstallMcpIntegrations(PurgeSession session, string pyrevitExe) {
            var item = $"MCP client registrations of {pyrevitExe} (pyrevit {McpUninstallArguments})";
            if (session.Options.DryRun) {
                session.ReportDeleted(item);
                return;
            }

            try {
                using var process = Process.Start(new ProcessStartInfo(pyrevitExe, McpUninstallArguments) { UseShellExecute = false });
                if (!process.WaitForExit(McpUninstallTimeoutMilliseconds)) {
                    process.Kill(entireProcessTree: true);
                    process.WaitForExit();
                    throw new TimeoutException($"pyrevit.exe did not finish within {McpUninstallTimeoutMilliseconds / 1000} seconds and was stopped.");
                }
                if (process.ExitCode != 0)
                    throw new InvalidOperationException($"pyrevit.exe exited with code {process.ExitCode}.");
                session.ReportDeleted(item);
            }
            catch (Exception ex) {
                session.ReportFailed(item, ex);
            }
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
