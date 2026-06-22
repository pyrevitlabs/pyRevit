using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.DotNet.Extensions;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<SeedProductDataModule>]
[DependsOn<SetProductDataModule>]
public sealed class BuildLabsModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var configuration = buildOptions.Value.Configuration;
        await context.DotNet().Build(new ModularPipelines.DotNet.Options.DotNetBuildOptions
        {
            ProjectSolution = PyRevitPaths.LabsSolution,
            Configuration = configuration,
        }, cancellationToken: cancellationToken);

        Directory.CreateDirectory(PyRevitPaths.BinPath);
        var tempRoot = Path.Combine(Path.GetTempPath(), "pyrevit-build-" + Guid.NewGuid().ToString("N"));
        var cliDir = Path.Combine(tempRoot, "cli");
        var doctorDir = Path.Combine(tempRoot, "doctor");

        try
        {
            await PublishProject(context, PyRevitPaths.LabsCliProject, cliDir, configuration, cancellationToken);
            await PublishProject(context, PyRevitPaths.LabsDoctorProject, doctorDir, configuration, cancellationToken);
            MergePublishOutput(doctorDir, PyRevitPaths.BinPath);
            MergePublishOutput(cliDir, PyRevitPaths.BinPath);
        }
        finally
        {
            if (Directory.Exists(tempRoot))
            {
                Directory.Delete(tempRoot, recursive: true);
            }
        }
    }

    private static async Task PublishProject(
        IModuleContext context,
        string projectPath,
        string publishDir,
        string configuration,
        CancellationToken cancellationToken)
    {
        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet")
            {
                Arguments =
                [
                    "publish",
                    projectPath,
                    "-c",
                    configuration,
                    "-f",
                    "net8.0-windows",
                    "-o",
                    publishDir,
                ],
            },
            cancellationToken: cancellationToken);
    }

    private static void MergePublishOutput(string sourceRoot, string destinationBin)
    {
        if (!Directory.Exists(sourceRoot))
        {
            return;
        }

        foreach (var sourceFile in Directory.EnumerateFiles(sourceRoot, "*", SearchOption.AllDirectories))
        {
            var relativePath = Path.GetRelativePath(sourceRoot, sourceFile);
            var destinationFile = Path.Combine(destinationBin, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(destinationFile)!);
            File.Copy(sourceFile, destinationFile, overwrite: true);
        }
    }
}
