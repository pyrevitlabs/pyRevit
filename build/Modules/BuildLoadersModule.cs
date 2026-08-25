using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildIronPythonDepsModule>]
public sealed class BuildLoadersModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var configuration = buildOptions.Value.Configuration;

        await DotNetBuildHelper.BuildProjectAsync(
            context,
            PyRevitPaths.Loader2712Project,
            configuration,
            cancellationToken);

        await DotNetBuildHelper.BuildProjectAsync(
            context,
            PyRevitPaths.Loader342Project,
            configuration,
            cancellationToken);
    }
}
