using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<ResolveVersioningModule>]
public sealed class StampVersionModule(IOptions<BuildOptions> buildOptions) : Module<VersionInfo>
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithStampingGate(buildOptions).Build();
    protected override async Task<VersionInfo?> ExecuteAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionResult = await context.GetModule<ResolveVersioningModule>();
        var versionInfo = versionResult.ValueOrDefault
            ?? throw new InvalidOperationException("ResolveVersioningModule did not produce a version.");

        VersionHelper.ReplaceVersionInFiles(PyRevitPaths.VersionFiles, versionInfo.BuildVersion);
        File.WriteAllText(PyRevitPaths.InstallVersionFile, versionInfo.InstallVersion);
        VersionHelper.ReplaceVersionInFiles(PyRevitPaths.InstallerScripts, versionInfo.InstallVersion);
        XmlHelper.SetChocoVersion(
            PyRevitPaths.PyRevitChocoNuspec,
            versionInfo.InstallVersion,
            VersionHelper.GetReleaseTagUrl(versionInfo.BuildVersionUrlSafe));
        XmlHelper.SetMsiVersion(PyRevitPaths.PyRevitCommonMsiProps, versionInfo.InstallVersion);

        return versionInfo;
    }
}
