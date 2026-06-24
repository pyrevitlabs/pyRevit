using System.Text.Json;
using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<StageBinAssetsModule>]
[DependsOn<ResolveVersioningModule>]
public sealed class WriteCiBinManifestModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionResult = await context.GetModule<ResolveVersioningModule>();
        var versionInfo = versionResult.ValueOrDefault
            ?? throw new InvalidOperationException("ResolveVersioningModule did not produce a version.");

        var sha = Environment.GetEnvironmentVariable("GITHUB_SHA") ?? string.Empty;
        var branch = Environment.GetEnvironmentVariable("GITHUB_REF_NAME")
            ?? Environment.GetEnvironmentVariable("GITHUB_HEAD_REF")
            ?? string.Empty;
        var runId = Environment.GetEnvironmentVariable("GITHUB_RUN_ID") ?? string.Empty;
        var artifactName = string.IsNullOrEmpty(sha) ? string.Empty : $"unsigned-bin-{sha}";

        var manifest = new
        {
            sha,
            branch,
            build_version = versionInfo.BuildVersion,
            artifact_name = artifactName,
            workflow_run_id = runId,
            channel = buildOptions.Value.Channel,
        };

        var manifestPath = Path.Combine(PyRevitPaths.Root, "ci-bin-manifest.json");
        var json = JsonSerializer.Serialize(manifest, new JsonSerializerOptions { WriteIndented = true });
        await File.WriteAllTextAsync(manifestPath, json, cancellationToken);

        var artifactManifestPath = Path.Combine(PyRevitPaths.BinPath, "ci-bin-manifest.json");
        await File.WriteAllTextAsync(artifactManifestPath, json, cancellationToken);
    }
}
