using System.Diagnostics;
using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildLabsModule>]
public sealed class CheckDeployLocksModule : Module
{
    private static readonly string[] SentinelFiles =
    [
        "IronPython.dll",
        "Microsoft.Scripting.dll",
    ];

    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var engineDir = Path.Combine(PyRevitPaths.BinPath, "netfx", "engines", "IPY342");
        var lockedFiles = SentinelFiles
            .Select(name => Path.Combine(engineDir, name))
            .Where(FileLockHelper.IsFileLocked)
            .ToList();

        if (lockedFiles.Count == 0)
        {
            return Task.CompletedTask;
        }

        var revitRunning = Process.GetProcessesByName("Revit").Length > 0;
        if (!revitRunning)
        {
            return Task.CompletedTask;
        }

        throw new InvalidOperationException(
            "Close Revit before rebuilding pyRevit when your dev clone uses this repository's bin/ folder. " +
            "Revit locks engine DLLs under bin/netfx/engines/IPY342/. " +
            "Locked files: " + string.Join(", ", lockedFiles.Select(Path.GetFileName)));
    }
}
