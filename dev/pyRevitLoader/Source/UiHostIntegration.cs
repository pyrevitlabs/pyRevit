using PyRevitLabs.UI.Client;
using System;
using System.Diagnostics;
using System.IO;

namespace PyRevitLoader
{
    internal static class UiHostIntegration
    {
        private const string EnableEnvironmentVariable = "PYREVIT_UI_HOST_POC";
        private static UiHostSession _session;
        private static readonly string IntegrationLogPath = Path.Combine(
            Path.GetTempPath(), $"pyrevit-ui-integration-{Process.GetCurrentProcess().Id}.log");

        internal static void Start(string loaderPath)
        {
            WriteLog($"start requested loaderPath={loaderPath} env={Environment.GetEnvironmentVariable(EnableEnvironmentVariable) ?? "<null>"}");

            if (!IsEnabled())
            {
                WriteLog("disabled");
                return;
            }

            if (_session != null)
            {
                WriteLog("host session already active");
                return;
            }

            try
            {
                var hostPath = ResolveHostPath(loaderPath);
                if (hostPath == null)
                {
                    WriteLog("host binary not found");
                    return;
                }

                var processId = Process.GetCurrentProcess().Id;
                var pipeName = $"pyrevit-ui-revit-{processId}-{Guid.NewGuid():N}";
                var logPath = Path.Combine(Path.GetTempPath(), $"pyrevit-ui-host-revit-{processId}.log");

                WriteLog($"starting host path={hostPath} pipe={pipeName}");
                _session = UiHostLauncher.StartAsync(
                    hostPath,
                    pipeName,
                    logPath,
                    "pyrevit-loader").GetAwaiter().GetResult();

                var hostInfo = _session.GetHostInfoAsync().GetAwaiter().GetResult();
                WriteLog(
                    $"ready hostPid={hostInfo.HostProcessId} " +
                    $"protocol={hostInfo.ProtocolVersion} version={hostInfo.HostVersion} log={logPath}");
            }
            catch (Exception ex)
            {
                WriteLog($"startup failed: {ex}");
                Stop();
            }
        }

        internal static void Stop()
        {
            if (_session == null)
                return;

            try
            {
                _session.Dispose();
                WriteLog("stopped");
            }
            catch (Exception ex)
            {
                WriteLog($"shutdown failed: {ex}");
            }
            finally
            {
                _session = null;
            }
        }

        private static void WriteLog(string message)
        {
            var line = $"{DateTimeOffset.Now:O} [UI-HOST-INTEGRATION] {message}";
            Trace.WriteLine(line);
            try
            {
                File.AppendAllText(IntegrationLogPath, line + Environment.NewLine);
            }
            catch
            {
            }
        }

        private static bool IsEnabled()
        {
            var value = Environment.GetEnvironmentVariable(EnableEnvironmentVariable);
            return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(value, "true", StringComparison.OrdinalIgnoreCase);
        }

        private static string ResolveHostPath(string loaderPath)
        {
            var engineFolder = Directory.GetParent(loaderPath);
            var runtimeFolder = engineFolder?.Parent;
            var binFolder = runtimeFolder?.Parent;
            if (binFolder == null)
                return null;

            var hostFolder = Path.Combine(binFolder.FullName, "ui-host");
            var executablePath = Path.Combine(hostFolder, "pyrevit-ui-host.exe");
            if (File.Exists(executablePath))
                return executablePath;

            var assemblyPath = Path.Combine(hostFolder, "pyrevit-ui-host.dll");
            return File.Exists(assemblyPath) ? assemblyPath : null;
        }
    }
}
