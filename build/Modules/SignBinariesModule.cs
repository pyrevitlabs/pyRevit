using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class SignBinariesModule(
    IOptions<BuildOptions> buildOptions,
    IOptions<SigningOptions> signingOptions) : Module
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithSigningGate(signingOptions).Build();
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var files = SigningHelper.FindPyRevitBinaries(PyRevitPaths.BinPath).ToArray();
        await SigningHelper.SignFilesAsync(
            context,
            signingOptions.Value,
            buildOptions.Value,
            files,
            "Binaries",
            cancellationToken);
    }
}
