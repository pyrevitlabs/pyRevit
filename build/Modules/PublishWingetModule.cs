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

        await RunWingetCreateUpdate(
            context,
            publishOptions.Value,
            "pyRevit.pyRevit",
            versionInfo.InstallVersion,
            pyRevitUrls,
            outputDir,
            cancellationToken);

        await RunWingetCreateUpdate(
            context,
            publishOptions.Value,
            "pyRevit.pyRevit.CLI",
            versionInfo.InstallVersion,
            cliUrls,
            outputDir,
            cancellationToken);
    }

    private static async Task RunWingetCreateUpdate(
        IModuleContext context,
        PublishOptions publishOptions,
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

        if (!string.IsNullOrWhiteSpace(publishOptions.WingetToken))
        {
            arguments.AddRange(["-t", publishOptions.WingetToken]);
        }

        if (publishOptions.SubmitWinget)
        {
            arguments.Add("-s");
        }

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(publishOptions.WingetCreateExe)
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
