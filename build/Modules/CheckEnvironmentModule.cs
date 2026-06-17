using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class CheckEnvironmentModule(IOptions<BuildOptions> buildOptions) : Module
{
    private static readonly (string Name, Func<string?> Resolver)[] CoreTools =
    [
        ("dotnet", static () => ToolResolutionHelper.ResolveOnPath("dotnet")),
        ("go", static () => ToolResolutionHelper.ResolveOnPath("go")),
    ];

    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var missing = CoreTools
            .Where(tool => string.IsNullOrWhiteSpace(tool.Resolver()))
            .Select(tool => tool.Name)
            .ToList();

        if (buildOptions.Value.RequireInstallerTooling)
        {
            if (string.IsNullOrWhiteSpace(ToolResolutionHelper.ResolveMsBuildExecutable()))
            {
                missing.Add("msbuild");
            }
        }

        if (missing.Count > 0)
        {
            throw new InvalidOperationException("Missing required build tools: " + string.Join(", ", missing));
        }

        context.Summary.KeyValue("Build", "Configuration", buildOptions.Value.Configuration);
        return Task.CompletedTask;
    }
}
