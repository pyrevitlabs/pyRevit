using System.Security.Cryptography;
using System.Text.RegularExpressions;
using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<SignDistInstallersModule>(Optional = true)]
public sealed class BuildChocoModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.ReadVersionInfo();
        var installerName = string.Format(PyRevitPaths.PyRevitCliAdminInstallerName, versionInfo.InstallVersion) + ".exe";
        var installerPath = Path.Combine(PyRevitPaths.DistPath, installerName);
        if (!File.Exists(installerPath))
        {
            throw new FileNotFoundException("Signed CLI admin installer was not found.", installerPath);
        }

        var downloadUrl = VersionHelper.GetReleaseDownloadBaseUrl(versionInfo.BuildVersionUrlSafe) + installerName;
        var checksum = ComputeSha256(installerPath);
        RewriteChocoInstallScript(downloadUrl, checksum);

        Directory.CreateDirectory(PyRevitPaths.DistPath);
        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("choco")
            {
                Arguments =
                [
                    "pack",
                    PyRevitPaths.PyRevitChocoNuspec,
                    "--outdir",
                    PyRevitPaths.DistPath,
                ],
            },
            cancellationToken: cancellationToken);
    }

    private static string ComputeSha256(string filePath)
    {
        using var stream = File.OpenRead(filePath);
        using var sha256 = SHA256.Create();
        return Convert.ToHexString(sha256.ComputeHash(stream)).ToUpperInvariant();
    }

    private static void RewriteChocoInstallScript(string downloadUrl, string checksum)
    {
        var lines = File.ReadAllLines(PyRevitPaths.PyRevitChocoInstallScript).ToList();
        for (var index = 0; index < lines.Count; index++)
        {
            if (Regex.IsMatch(lines[index], @"^\$url64\s+="))
            {
                lines[index] = $"$url64      = '{downloadUrl}'";
            }
            else if (Regex.IsMatch(lines[index], @"^\s*checksum64\s+="))
            {
                lines[index] = $"  checksum64    = '{checksum}'";
            }
        }

        File.WriteAllLines(PyRevitPaths.PyRevitChocoInstallScript, lines);
    }
}
