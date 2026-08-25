using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Options;

namespace Build.Helpers;

public static class DotNetBuildHelper
{
    public static async Task BuildProjectAsync(
        IModuleContext context,
        string projectOrSolutionPath,
        string configuration,
        CancellationToken cancellationToken)
    {
        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet")
            {
                Arguments =
                [
                    "build",
                    projectOrSolutionPath,
                    "-c",
                    configuration,
                ],
            },
            cancellationToken: cancellationToken);
    }

    public static async Task PublishProjectAsync(
        IModuleContext context,
        string projectOrSolutionPath,
        string configuration,
        string framework,
        string outputDirectory,
        CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(outputDirectory);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet")
            {
                Arguments =
                [
                    "publish",
                    projectOrSolutionPath,
                    "-c",
                    configuration,
                    "-f",
                    framework,
                    "-o",
                    outputDirectory,
                ],
            },
            cancellationToken: cancellationToken);
    }
}
