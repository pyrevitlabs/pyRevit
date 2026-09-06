using PyRevitLabs.UI.Client;
using System;
using System.Diagnostics;
using System.IO;

using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.SessionManager;

namespace PyRevitLoader
{
    internal static class UiHostIntegration
    {
        private const string EnableEnvironmentVariable = "PYREVIT_UI_HOST_POC";
        private static UiHostSession _session;

        internal static UiHostSession Session => _session;
        private static readonly ILogger Logger = ServiceFactory.CreateLogger();

        internal static void Start(string loaderPath)
        {
            var enabled = IsEnabled(out var enableSource);
            WriteLog($"start requested loaderPath={loaderPath} enabled={enabled} source={enableSource}");

            if (!enabled)
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

                WriteLog($"host resolved path={hostPath}");
                WriteLog($"starting host pipe={pipeName}");
                _session = UiHostLauncher.StartAsync(
                    hostPath,
                    pipeName,
                    "pyrevit-loader",
                    WriteHostDiagnostic).GetAwaiter().GetResult();

                IsolatedUiService.Attach(_session);
                WriteLog($"host process connected hostPid={_session.HostInfo.HostProcessId}");
                WriteLog("requesting host.info");
                var hostInfo = _session.GetHostInfoAsync().GetAwaiter().GetResult();
                WriteLog(
                    $"ready hostPid={hostInfo.HostProcessId} " +
                    $"protocol={hostInfo.ProtocolVersion} version={hostInfo.HostVersion}");
            }
            catch (Exception ex)
            {
                WriteError($"startup failed: {ex}");
                Stop();
            }
        }

        internal static void Stop()
        {
            if (_session == null)
                return;

            try
            {
                IsolatedUiService.Detach(_session);
                _session.Dispose();
                WriteLog("stopped");
            }
            catch (Exception ex)
            {
                WriteError($"shutdown failed: {ex}");
            }
            finally
            {
                _session = null;
            }
        }

        internal static void WriteLog(string message)
        {
            try { Logger.Debug($"[IsolatedUI] {message}"); }
            catch { Trace.WriteLine($"[IsolatedUI] {message}"); }
        }

        private static void WriteHostDiagnostic(string message)
        {
            if (!string.IsNullOrWhiteSpace(message))
                WriteLog($"host {message}");
        }

        private static void WriteError(string message)
        {
            try { Logger.Error($"[IsolatedUI] {message}"); }
            catch { Trace.WriteLine($"[IsolatedUI] ERROR {message}"); }
        }

        private static bool IsEnabled(out string source)
        {
            var environmentValue = Environment.GetEnvironmentVariable(EnableEnvironmentVariable);
            if (!string.IsNullOrWhiteSpace(environmentValue))
            {
                if (string.Equals(environmentValue, "1", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(environmentValue, "true", StringComparison.OrdinalIgnoreCase))
                {
                    source = $"environment:{EnableEnvironmentVariable}={environmentValue}";
                    return true;
                }

                if (string.Equals(environmentValue, "0", StringComparison.OrdinalIgnoreCase)
                    || string.Equals(environmentValue, "false", StringComparison.OrdinalIgnoreCase))
                {
                    source = $"environment:{EnableEnvironmentVariable}={environmentValue}";
                    return false;
                }
            }

            try
            {
                var config = PyRevitConfig.Load();
                source = $"config:{config.ConfigPath} isolated_ui={config.IsolatedUi}";
                return config.IsolatedUi;
            }
            catch (Exception ex)
            {
                source = $"config-error:{ex.GetType().Name}:{ex.Message}";
                return false;
            }
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
