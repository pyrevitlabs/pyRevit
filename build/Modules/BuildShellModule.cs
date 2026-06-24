using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

// The interactive shell ships into the active engine folder (next to the loader/DLR it runs
// against), so it must build after the loaders/runtime have deployed the IronPython/DLR there.
// Building the per-fork configurations also runs the csproj DeployShell target, which copies
// pyRevitLabs.PyRevit.Shell.dll + ICSharpCode.AvalonEdit.dll into each engine folder.
[DependsOn<BuildRuntimeModule>]
public sealed class BuildShellModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var configuration = buildOptions.Value.Configuration;

        await DotNetBuildHelper.BuildProjectAsync(
            context,
            PyRevitPaths.ShellProject,
            configuration + " IPY2712PR",
            cancellationToken);

        await DotNetBuildHelper.BuildProjectAsync(
            context,
            PyRevitPaths.ShellProject,
            configuration + " IPY342",
            cancellationToken);
    }
}