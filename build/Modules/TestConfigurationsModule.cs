using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<BuildRunnersModule>]
/// <summary>
/// Runs configuration backend and compatibility tests after their build outputs
/// are available.
/// </summary>
public sealed class TestConfigurationsModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var configuration = buildOptions.Value.Configuration;

        await RunTestsAsync(
            context,
            PyRevitPaths.ConfigurationsTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.IniConfigurationsTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.ExtensionParserTestProject,
            configuration,
            [
                "--no-build",
                "-f",
                "net8.0-windows",
                "--filter",
                "FullyQualifiedName~ConfigParityTests|FullyQualifiedName~PyRevitConfigsFacadeTests",
            ],
            cancellationToken);
    }

    private static async Task RunTestsAsync(
        IModuleContext context,
        string projectPath,
        string configuration,
        IReadOnlyList<string> additionalArguments,
        CancellationToken cancellationToken)
    {
        var arguments = new List<string>
        {
            "test",
            projectPath,
            "-c",
            configuration,
        };
        arguments.AddRange(additionalArguments);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet")
            {
                Arguments = arguments,
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.Root,
            },
            cancellationToken: cancellationToken);
    }
}
