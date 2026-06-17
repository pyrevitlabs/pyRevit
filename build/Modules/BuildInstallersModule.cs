using Build.Helpers;
using Build.Models;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<RestoreStampedMetadataModule>]
[DependsOn<SignBinariesModule>(Optional = true)]
public sealed class BuildInstallersModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (!File.Exists(PyRevitPaths.IsccPath))
        {
            throw new FileNotFoundException("Inno Setup compiler was not found.", PyRevitPaths.IsccPath);
        }

        foreach (var script in PyRevitPaths.InstallerScripts)
        {
            await context.Shell.Command.ExecuteCommandLineTool(
                new GenericCommandLineToolOptions(PyRevitPaths.IsccPath)
                {
                    Arguments = [Path.GetFullPath(script)],
                },
                cancellationToken: cancellationToken);
        }

        var msbuild = ToolResolutionHelper.ResolveMsBuildExecutable()
            ?? throw new FileNotFoundException("MSBuild was not found. Install Visual Studio Build Tools or run from a Developer shell.");

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(msbuild)
            {
                Arguments = [Path.GetFullPath(PyRevitPaths.PyRevitCliMsiProject)],
            },
            cancellationToken: cancellationToken);
    }
}
