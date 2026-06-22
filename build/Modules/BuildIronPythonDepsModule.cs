using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Seeds IPY2712PR engine folders with IronPython/DLR assemblies required before loader compile.
/// Mirrors <c>pipenv run pyrevit build deps</c> IronPython2 steps from dev/_labs.py.
/// </summary>
[DependsOn<CheckDeployLocksModule>]
public sealed class BuildIronPythonDepsModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var configuration = buildOptions.Value.Configuration;

        await DotNetBuildHelper.PublishProjectAsync(
            context,
            PyRevitPaths.IronPython2Solution,
            configuration,
            "net48",
            PyRevitPaths.Engines2712NetFxPath,
            cancellationToken);

        await DotNetBuildHelper.PublishProjectAsync(
            context,
            PyRevitPaths.IronPython2LibProject,
            configuration,
            "netstandard2.0",
            PyRevitPaths.Engines2712NetCorePath,
            cancellationToken);

        await DotNetBuildHelper.PublishProjectAsync(
            context,
            PyRevitPaths.IronPython2ModulesProject,
            configuration,
            "netstandard2.0",
            PyRevitPaths.Engines2712NetCorePath,
            cancellationToken);

        await DotNetBuildHelper.PublishProjectAsync(
            context,
            PyRevitPaths.IronPython2SqliteProject,
            configuration,
            "netstandard2.0",
            PyRevitPaths.Engines2712NetCorePath,
            cancellationToken);

        await DotNetBuildHelper.PublishProjectAsync(
            context,
            PyRevitPaths.IronPython2WpfProject,
            configuration,
            "net6.0-windows",
            PyRevitPaths.Engines2712NetCorePath,
            cancellationToken);
    }
}
