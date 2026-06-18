using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<BuildAutocompModule>]
public sealed class VerifyLibGit2Module : Module{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var shell = ToolResolutionHelper.ResolvePowerShellExecutable();

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(shell)
            {
                Arguments = ["-NoProfile", "-File", PyRevitPaths.VerifyLibGit2Script],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.Root,
            },
            cancellationToken: cancellationToken);
    }
}
