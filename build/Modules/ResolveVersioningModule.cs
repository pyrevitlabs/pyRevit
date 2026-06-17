using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class ResolveVersioningModule(IOptions<BuildOptions> buildOptions) : Module<VersionInfo>
{
    protected override Task<VersionInfo?> ExecuteAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var baseVersion = VersionHelper.ReadBuildVersion();
        var buildVersion = VersionHelper.UpdateBuildNumber(baseVersion.Split('+')[0].Split('-')[0]);
        buildVersion = VersionHelper.ApplyChannel(buildVersion, buildOptions.Value.Channel);
        var versionInfo = VersionHelper.CreateVersionInfo(buildVersion);
        context.Summary.KeyValue("Build", "Version", versionInfo.BuildVersion);
        context.Summary.KeyValue("Build", "InstallVersion", versionInfo.InstallVersion);
        return Task.FromResult<VersionInfo?>(versionInfo);
    }
}
