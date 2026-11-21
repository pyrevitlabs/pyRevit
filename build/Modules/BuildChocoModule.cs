using System.Security.Cryptography;
using System.Text.RegularExpressions;
using Build.Helpers;
using Build.Models;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<RejectTestSignedBinariesModule>]
[DependsOn<SignDistInstallersModule>(Optional = true)]
public sealed class BuildChocoModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.ReadVersionInfo();
        Directory.CreateDirectory(PyRevitPaths.DistPath);

        foreach (var package in PyRevitPaths.ChocoPackages)
        {
            var installerName = string.Format(package.InstallerNameFormat, versionInfo.InstallVersion) + ".exe";
            var installerPath = Path.Combine(PyRevitPaths.DistPath, installerName);
            if (!File.Exists(installerPath))
            {
                throw new FileNotFoundException(
                    $"Signed admin installer for Chocolatey package '{package.Id}' was not found.",
                    installerPath);
            }

            var downloadUrl = VersionHelper.GetReleaseDownloadBaseUrl(versionInfo.BuildVersionUrlSafe) + installerName;
            RewriteChocoInstallScript(package, downloadUrl, ComputeSha256(installerPath));

            await context.Shell.Command.ExecuteCommandLineTool(
                new GenericCommandLineToolOptions("choco")
                {
                    Arguments =
                    [
                        "pack",
                        package.Nuspec,
                        "--outdir",
                        PyRevitPaths.DistPath,
                    ],
                },
                cancellationToken: cancellationToken);
        }
    }

    private static string ComputeSha256(string filePath)
    {
        using var stream = File.OpenRead(filePath);
        using var sha256 = SHA256.Create();
        return Convert.ToHexString(sha256.ComputeHash(stream)).ToUpperInvariant();
    }

    private static void RewriteChocoInstallScript(ChocoPackage package, string downloadUrl, string checksum)
    {
        var lines = File.ReadAllLines(package.InstallScript).ToList();
        for (var index = 0; index < lines.Count; index++)
        {
            if (Regex.IsMatch(lines[index], @"^\$url64\s+="))
            {
                lines[index] = ReplaceQuotedValue(lines[index], downloadUrl);
            }
            else if (Regex.IsMatch(lines[index], @"^\s*checksum64\s+="))
            {
                lines[index] = ReplaceQuotedValue(lines[index], checksum);
            }
        }

        File.WriteAllLines(package.InstallScript, lines);
    }

    private static string ReplaceQuotedValue(string line, string value)
        => Regex.Replace(line, "'[^']*'", _ => $"'{value}'", RegexOptions.None, TimeSpan.FromSeconds(1));
}
