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
[DependsOn<BuildShellModule>]
/// <summary>
/// Runs configuration backend, CPython interpreter lifecycle, CPython env vars, agent runtime
/// guard, renderer load-context, <c>pyrevit.forms</c> engine parity, and compatibility tests
/// after their build outputs are available, plus the Python 3 compatibility checker's own unit
/// tests.
/// </summary>
/// <remarks>
/// The checker tests need a <c>python</c> 3 interpreter on <c>PATH</c>. The forms tests show real
/// WPF windows, so the runner must have a desktop session.
/// </remarks>
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
            PyRevitPaths.CPythonRuntimeTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.EnvVarsRuntimeTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.AgentRuntimeTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.CliTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.RendererTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.FormsBindingTestProject,
            configuration,
            [],
            cancellationToken);

        await RunTestsAsync(
            context,
            PyRevitPaths.FormsTestProject,
            configuration,
            [],
            cancellationToken);

        foreach (var engine in new[] { "IPY2712PR", "IPY342" })
            await RunTestsAsync(
                context,
                PyRevitPaths.FormsIronPythonTestProject,
                configuration,
                [$"-p:IronPythonVersion={engine}"],
                cancellationToken);

        foreach (var engine in new[] { "IPY2712PR", "IPY342" })
            await RunTestsAsync(
                context,
                PyRevitPaths.ShellTestProject,
                configuration,
                [
                    $"-p:ShellEnginesDirectory={PyRevitPaths.EnginesNetCorePath}",
                    $"-p:IronPythonVersion={engine}",
                ],
                cancellationToken);

        foreach (string framework in new[] { "net48", "net8.0-windows" })
            await RunTestsAsync(
                context,
                PyRevitPaths.PyRevitUnitTestProject,
                configuration,
                [
                    "--no-build",
                    "-f",
                    framework,
                    "--filter",
                    "FullyQualifiedName~PyRevitConfigsSeedTests|FullyQualifiedName~RevitProductDataTests|FullyQualifiedName~BelowMinimumProductReportingTests|FullyQualifiedName~AttachableProductTests|FullyQualifiedName~AttachableProductFilterTests|FullyQualifiedName~PyRevitBuildVersionTests|FullyQualifiedName~DeployedVersionTests|FullyQualifiedName~SystemPathTests",
                ],
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
                "FullyQualifiedName~ConfigParityTests|FullyQualifiedName~PyRevitConfigsFacadeTests|FullyQualifiedName~EmojisTests|FullyQualifiedName~ScriptEngineManagerTests|FullyQualifiedName~ScriptOutputUiGateTests|FullyQualifiedName~RevitThemeDetectorTests|FullyQualifiedName~EnvDictionaryTests",
            ],
            cancellationToken);

        await RunPythonTestsAsync(context, "test_check_py3_compat.py", cancellationToken);
    }

    private static async Task RunPythonTestsAsync(
        IModuleContext context,
        string pattern,
        CancellationToken cancellationToken)
    {
        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("python")
            {
                Arguments = ["-m", "unittest", "discover", "-s", Path.Combine("dev", "scripts"), "-p", pattern],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.Root,
            },
            cancellationToken: cancellationToken);
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
