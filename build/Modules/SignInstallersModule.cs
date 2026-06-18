using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildInstallersModule>]
public sealed class SignDistInstallersModule(
    IOptions<BuildOptions> buildOptions,
    IOptions<SigningOptions> signingOptions) : Module
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithSigningGate(signingOptions).Build();
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.ReadVersionInfo();
        var files = new List<string>();

        files.AddRange(GetInstallerFiles(
            versionInfo.InstallVersion,
            PyRevitPaths.PyRevitInstallerName,
            PyRevitPaths.PyRevitAdminInstallerName,
            PyRevitPaths.PyRevitCliInstallerName,
            PyRevitPaths.PyRevitCliAdminInstallerName));

        var msiPath = Path.Combine(
            PyRevitPaths.DistPath,
            string.Format(PyRevitPaths.PyRevitCliAdminInstallerName, versionInfo.InstallVersion) + ".msi");
        if (File.Exists(msiPath))
        {
            files.Add(msiPath);
        }

        await SigningHelper.SignFilesAsync(
            context,
            signingOptions.Value,
            buildOptions.Value,
            files,
            "Installers",
            cancellationToken);
    }

    private static IEnumerable<string> GetInstallerFiles(string installVersion, params string[] nameFormats)
    {
        foreach (var nameFormat in nameFormats)
        {
            var path = Path.Combine(PyRevitPaths.DistPath, string.Format(nameFormat, installVersion) + ".exe");
            if (File.Exists(path))
            {
                yield return path;
            }
        }
    }

}
