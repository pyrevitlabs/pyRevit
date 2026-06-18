using Build.Helpers;
using Build.Options;
using EnumerableAsyncProcessor.Extensions;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Git.Extensions;
using ModularPipelines.GitHub.Attributes;
using ModularPipelines.GitHub.Extensions;
using ModularPipelines.Modules;
using Octokit;

namespace Build.Modules;

[SkipIfNoGitHubToken]
[DependsOn<GenerateReleaseNotesModule>]
[DependsOn<SignChocoPackageModule>]
public sealed class PublishGithubReleaseModule(IOptions<PublishOptions> publishOptions) : Module<string>
{
    protected override async Task<string?> ExecuteAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.ReadVersionInfo();
        var notesResult = await context.GetModule<GenerateReleaseNotesModule>();
        var releaseNotes = notesResult.ValueOrDefault ?? string.Empty;

        var repositoryInfo = context.GitHub().RepositoryInfo;
        var newRelease = new NewRelease("v" + versionInfo.BuildVersion)
        {
            Name = "pyRevit v" + versionInfo.InstallVersion,
            Body = releaseNotes,
            Draft = publishOptions.Value.DraftRelease,
            Prerelease = versionInfo.IsWip,
        };

        var release = await context.GitHub().Client.Repository.Release.Create(
            repositoryInfo.Owner,
            repositoryInfo.RepositoryName,
            newRelease);

        var assetFiles = Directory.Exists(PyRevitPaths.DistPath)
            ? Directory.GetFiles(PyRevitPaths.DistPath)
                .Where(file =>
                    file.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)
                    || file.EndsWith(".msi", StringComparison.OrdinalIgnoreCase)
                    || file.EndsWith(".nupkg", StringComparison.OrdinalIgnoreCase))
                .ToArray()
            : [];

        await assetFiles
            .ForEachAsync(async filePath =>
            {
                await using var stream = File.OpenRead(filePath);
                var upload = new ReleaseAssetUpload
                {
                    ContentType = "application/octet-stream",
                    FileName = Path.GetFileName(filePath),
                    RawData = stream,
                };

                await context.GitHub().Client.Repository.Release.UploadAsset(release, upload, cancellationToken);
            }, cancellationToken)
            .ProcessInParallel();

        context.Summary.KeyValue("Deployment", "GitHub", release.HtmlUrl);
        return release.HtmlUrl;
    }

}
