using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

// Engine assemblies must be deployed before the shell can bind to the selected Python fork.
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
