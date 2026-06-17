using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<VerifyLibGit2Module>]
public sealed class StageReleaseMetadataModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithStampingGate(buildOptions).Build();
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var stagingRoot = Path.Combine(PyRevitPaths.Root, "ci-stamped");
        if (Directory.Exists(stagingRoot))
        {
            Directory.Delete(stagingRoot, recursive: true);
        }

        foreach (var sourceFile in PyRevitPaths.StampedReleaseMetadataFiles)
        {
            var relativePath = Path.GetRelativePath(PyRevitPaths.Root, sourceFile);
            var destinationFile = Path.Combine(stagingRoot, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(destinationFile)!);
            File.Copy(sourceFile, destinationFile, overwrite: true);
        }

        context.Summary.KeyValue("Artifacts", "StampedMetadata", stagingRoot);
        return Task.CompletedTask;
    }
}
