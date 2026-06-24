using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<BuildRuntimeModule>]
public sealed class BuildAutocompModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("go")
            {
                Arguments = ["get", "-u", "./..."],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.AutocompPath,
            },
            cancellationToken: cancellationToken);

        AutocompleteGenerator.Generate(PyRevitPaths.UsagePatterns, PyRevitPaths.AutocompSource);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("go")
            {
                Arguments = ["fmt", PyRevitPaths.AutocompSource],
            },
            cancellationToken: cancellationToken);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("go")
            {
                Arguments = ["build", "-o", PyRevitPaths.AutocompBin, PyRevitPaths.AutocompSource],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.AutocompPath,
            },
            cancellationToken: cancellationToken);
    }
}
