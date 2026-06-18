using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildRuntimeModule>]
public sealed class StageBinAssetsModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var binAssetsRoot = PyRevitPaths.BinAssetsPath;
        if (!Directory.Exists(binAssetsRoot))
        {
            throw new DirectoryNotFoundException($"Missing tracked bin assets at \"{binAssetsRoot}\".");
        }

        CommonCopyHelper.CopyDirectory(binAssetsRoot, PyRevitPaths.BinPath);

        var cenginesRoot = PyRevitPaths.CEnginesPath;
        var cenginesTarget = Path.Combine(PyRevitPaths.BinPath, "cengines");
        if (!Directory.Exists(cenginesRoot))
            throw new DirectoryNotFoundException($"Missing tracked CPython engines at \"{cenginesRoot}\".");

        // CPY3123 is the minimum engine required today; copy all of release/cengines/ for forward compatibility.
        var cpy3123Source = Path.Combine(cenginesRoot, "CPY3123");
        if (!Directory.Exists(cpy3123Source))
            throw new DirectoryNotFoundException($"Missing CPython 3.12.3 engine at \"{cpy3123Source}\".");

        CommonCopyHelper.CopyDirectory(cenginesRoot, cenginesTarget);

        foreach (var hostsTarget in PyRevitPaths.HostsDataTargets)
        {
            File.Copy(PyRevitPaths.HostsDataFile, hostsTarget, overwrite: true);
        }

        await Task.CompletedTask;
    }
}
