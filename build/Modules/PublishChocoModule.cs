using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<SignChocoPackageModule>]
public sealed class PublishChocoModule(IOptions<PublishOptions> publishOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(publishOptions.Value.ChocoToken))
        {
            return;
        }

        var versionInfo = VersionHelper.ReadVersionInfo();
        var packagePath = Path.Combine(
            PyRevitPaths.DistPath,
            string.Format(PyRevitPaths.PyRevitChocoNupkgName, versionInfo.InstallVersion));

        if (!File.Exists(packagePath))
        {
            throw new FileNotFoundException("Chocolatey package was not found.", packagePath);
        }

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("choco")
            {
                Arguments =
                [
                    "apikey",
                    "--key",
                    publishOptions.Value.ChocoToken,
                    "--source",
                    publishOptions.Value.ChocoSource,
                ],
            },
            cancellationToken: cancellationToken);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("choco")
            {
                Arguments =
                [
                    "push",
                    packagePath,
                    "-s",
                    publishOptions.Value.ChocoSource,
                ],
            },
            cancellationToken: cancellationToken);
    }

}
