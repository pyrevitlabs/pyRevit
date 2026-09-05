using System.Diagnostics;
using PyRevitLabs.UI.Client;

var hostPath = GetArgument(args, "--host") ?? throw new ArgumentException("--host is required.");
var pipeName = GetArgument(args, "--pipe") ?? $"pyrevit-ui-poc-{Environment.ProcessId}-{Guid.NewGuid():N}";
var logPath = GetArgument(args, "--log") ?? Path.Combine(Path.GetTempPath(), $"pyrevit-ui-host-{Environment.ProcessId}.log");

Trace.Listeners.Add(new ConsoleTraceListener());
Console.WriteLine($"[UI-PROBE] starting host={hostPath} pipe={pipeName}");

using var session = await UiHostLauncher.StartAsync(hostPath, pipeName, logPath, "pyrevit-ui-probe");
Console.WriteLine($"[UI-PROBE] handshake ok hostPid={session.HostInfo.HostProcessId}");

var info = await session.GetHostInfoAsync();
Require(info.ProtocolVersion == UiHostSession.ProtocolVersion, "protocol version mismatch");
Require(info.HostProcessId == session.HostInfo.HostProcessId, "host process id changed");

Console.WriteLine($"[UI-PROBE] host.info protocol={info.ProtocolVersion} pid={info.HostProcessId} version={info.HostVersion}");
Console.WriteLine("[UI-PROBE] PASS");
return 0;

static void Require(bool condition, string message)
{
    if (!condition)
        throw new InvalidOperationException(message);
}

static string? GetArgument(string[] values, string name)
{
    for (var i = 0; i < values.Length - 1; i++)
        if (string.Equals(values[i], name, StringComparison.OrdinalIgnoreCase))
            return values[i + 1];
    return null;
}
