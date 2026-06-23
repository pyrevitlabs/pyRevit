using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.GitHub.Attributes;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[SkipIfNoGitHubToken]
public sealed class PublishWingetModule(IOptions<PublishOptions> publishOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(publishOptions.Value.WingetToken))
        {
            return;
        }

        var versionInfo = VersionHelper.ReadVersionInfo();
        if (versionInfo.IsWip)
        {
            return;
        }

        var releaseTag = "v" + versionInfo.BuildVersion;
        var outputDir = Path.Combine(Path.GetTempPath(), "pyrevit-winget-manifests");
        Directory.CreateDirectory(outputDir);

        var pyRevitUrls = BuildPyRevitUrls(versionInfo, releaseTag);
        var cliUrls = BuildCliUrls(versionInfo, releaseTag);

        await PublishPackageAsync(
            context,
            publishOptions.Value,
            "pyRevit.pyRevit",
            versionInfo.InstallVersion,
            pyRevitUrls,
            outputDir,
            cancellationToken);

        await PublishPackageAsync(
            context,
            publishOptions.Value,
            "pyRevit.pyRevit.CLI",
            versionInfo.InstallVersion,
            cliUrls,
            outputDir,
            cancellationToken);
    }

    private static async Task PublishPackageAsync(
        IModuleContext context,
        PublishOptions options,
        string packageId,
        string installVersion,
        IEnumerable<string> urls,
        string outputDir,
        CancellationToken cancellationToken)
    {
        await RunWingetCreateGenerateAsync(
            context,
            options,
            packageId,
            installVersion,
            urls,
            outputDir,
            cancellationToken);

        var versionDir = WingetManifestHelper.FindVersionManifestDirectory(outputDir, packageId, installVersion);
        WingetManifestHelper.RemoveElevationProhibited(versionDir);

        if (!options.SubmitWinget)
        {
            return;
        }

        await RunWingetCreateSubmitAsync(
            context,
            options,
            packageId,
            installVersion,
            versionDir,
            cancellationToken);
    }

    private static async Task RunWingetCreateGenerateAsync(
        IModuleContext context,
        PublishOptions options,
        string packageId,
        string installVersion,
        IEnumerable<string> urls,
        string outputDir,
        CancellationToken cancellationToken)
    {
        var arguments = new List<string>
        {
            "update",
            packageId,
            "-v",
            installVersion,
            "-u",
        };
        arguments.AddRange(urls);
        arguments.AddRange(["-o", outputDir, "--no-open"]);

        if (!string.IsNullOrWhiteSpace(options.WingetToken))
        {
            arguments.AddRange(["-t", options.WingetToken]);
        }

        var wingetCreate = ToolResolutionHelper.ResolveWingetCreateExecutable(options.WingetCreateExe);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(wingetCreate)
            {
                Arguments = arguments,
            },
            cancellationToken: cancellationToken);
    }

    private static async Task RunWingetCreateSubmitAsync(
        IModuleContext context,
        PublishOptions options,
        string packageId,
        string installVersion,
        string versionDir,
        CancellationToken cancellationToken)
    {
        var arguments = new List<string>
        {
            "submit",
            versionDir,
            "-t",
            options.WingetToken,
            "--no-open",
            "-p",
            string.Format("New version: {0} version {1}", packageId, installVersion),
        };

        if (!string.IsNullOrWhiteSpace(options.WingetReplaceVersion))
        {
            arguments.Add("-r");
            arguments.Add(options.WingetReplaceVersion);
        }

        var wingetCreate = ToolResolutionHelper.ResolveWingetCreateExecutable(options.WingetCreateExe);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(wingetCreate)
            {
                Arguments = arguments,
            },
            cancellationToken: cancellationToken);
    }

    private static IEnumerable<string> BuildPyRevitUrls(VersionInfo versionInfo, string releaseTag)
    {
        var baseUrl = $"https://github.com/pyrevitlabs/pyRevit/releases/download/{releaseTag}/";
        yield return $"{baseUrl}pyRevit_{versionInfo.InstallVersion}_signed.exe|x86|user";
        yield return $"{baseUrl}pyRevit_{versionInfo.InstallVersion}_admin_signed.exe|x64|machine";
    }

    private static IEnumerable<string> BuildCliUrls(VersionInfo versionInfo, string releaseTag)
    {
        var baseUrl = $"https://github.com/pyrevitlabs/pyRevit/releases/download/{releaseTag}/";
        yield return $"{baseUrl}pyRevit_CLI_{versionInfo.InstallVersion}_signed.exe|x64|user";
        yield return $"{baseUrl}pyRevit_CLI_{versionInfo.InstallVersion}_admin_signed.exe|x64|machine";
        yield return $"{baseUrl}pyRevit_CLI_{versionInfo.InstallVersion}_admin_signed.msi|x64|machine";
    }

}
