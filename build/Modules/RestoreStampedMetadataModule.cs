using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Applies CI-stamped metadata downloaded from the stamped-release-metadata artifact
/// back onto the working tree before pack/sign steps run on a fresh checkout.
/// </summary>
public sealed class RestoreStampedMetadataModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var stagingRoot = Path.Combine(PyRevitPaths.Root, "ci-stamped");
        if (!Directory.Exists(stagingRoot))
        {
            context.Summary.KeyValue("Artifacts", "RestoredStampedFiles", "0 (ci-stamped not present)");
            return Task.CompletedTask;
        }

        var restoredFiles = 0;
        foreach (var sourceFile in Directory.EnumerateFiles(stagingRoot, "*", SearchOption.AllDirectories))
        {
            var relativePath = Path.GetRelativePath(stagingRoot, sourceFile);
            var destinationFile = Path.Combine(PyRevitPaths.Root, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(destinationFile)!);
            File.Copy(sourceFile, destinationFile, overwrite: true);
            restoredFiles++;
        }

        context.Summary.KeyValue("Artifacts", "RestoredStampedFiles", restoredFiles.ToString());
        return Task.CompletedTask;
    }
}
