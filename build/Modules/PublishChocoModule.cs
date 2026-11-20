using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

/// <summary>
/// Pushes the signed Chocolatey packages found in <c>dist/</c> to the Chocolatey community feed.
/// </summary>
/// <remarks>
/// Runs only in the <c>choco</c> mode, from <c>choco.yml</c> after the GitHub release is published, because the
/// packages download the installer from the release and Chocolatey moderation starts as soon as they are pushed.
/// The packages are the signed <c>.nupkg</c> files the release job attached to the draft release; this module
/// does not build or sign anything. A version the feed already has is skipped, so the mode can be re-run after
/// a partial failure.
/// </remarks>
public sealed class PublishChocoModule(IOptions<PublishOptions> publishOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(publishOptions.Value.ChocoToken))
        {
            return;
        }

        var packagePaths = Directory
            .GetFiles(PyRevitPaths.DistPath, "*.nupkg")
            .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
            .ToArray();

        if (packagePaths.Length == 0)
        {
            throw new FileNotFoundException(
                "No Chocolatey package (.nupkg) was found to push.",
                PyRevitPaths.DistPath);
        }

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("choco")
            {
                Arguments =
                [
                    "apikey",
                    "--key",
                    publishOptions.Value.ChocoToken,
                    "--source",
                    publishOptions.Value.ChocoSource,
                ],
            },
            cancellationToken: cancellationToken);

        foreach (var packagePath in packagePaths)
        {
            await PushPackageAsync(context, packagePath, cancellationToken);
        }
    }

    private async Task PushPackageAsync(
        IModuleContext context,
        string packagePath,
        CancellationToken cancellationToken)
    {
        try
        {
            await context.Shell.Command.ExecuteCommandLineTool(
                new GenericCommandLineToolOptions("choco")
                {
                    Arguments =
                    [
                        "push",
                        packagePath,
                        "-s",
                        publishOptions.Value.ChocoSource,
                    ],
                },
                cancellationToken: cancellationToken);
        }
        catch (Exception ex) when (IsAlreadyPublishedConflict(ex))
        {
            context.Summary.KeyValue(
                "Choco",
                Path.GetFileNameWithoutExtension(packagePath),
                "skipped (version already published)");
        }
    }

    private static bool IsAlreadyPublishedConflict(Exception exception)
    {
        for (var current = exception; current is not null; current = current.InnerException)
        {
            var message = current.Message;
            if (message.Contains("409", StringComparison.Ordinal)
                || message.Contains("Conflict", StringComparison.OrdinalIgnoreCase)
                || message.Contains("already exists", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }

}
