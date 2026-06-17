using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.DotNet.Extensions;
using ModularPipelines.DotNet.Options;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildLoadersModule>]
public sealed class BuildRuntimeModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var configuration = buildOptions.Value.Configuration;
        await context.DotNet().Build(new DotNetBuildOptions
        {
            ProjectSolution = PyRevitPaths.RuntimeSolution,
            Configuration = configuration + " IPY2712PR",
        }, cancellationToken: cancellationToken);

        await context.DotNet().Build(new DotNetBuildOptions
        {
            ProjectSolution = PyRevitPaths.RuntimeSolution,
            Configuration = configuration + " IPY342",
        }, cancellationToken: cancellationToken);
    }
}
