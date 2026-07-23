using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class WingetManifestHelperTests
{
    [TestMethod]
    public void RemoveElevationProhibited_stripsLineFromUserInstallerYaml()
    {
        var root = Path.Combine(Path.GetTempPath(), "winget-test-" + Guid.NewGuid().ToString("N"));
        var versionDir = Path.Combine(root, "manifests", "p", "pyRevit", "pyRevit", "6.5.0.26173");
        Directory.CreateDirectory(versionDir);

        var installerPath = Path.Combine(versionDir, "pyRevit.pyRevit.installer.yaml");
        File.WriteAllLines(
            installerPath,
            [
                "Installers:",
                "- Architecture: x86",
                "  Scope: user",
                "  ElevationRequirement: elevationProhibited",
                "  InstallerSha256: ABC",
                "- Architecture: x64",
                "  Scope: machine",
                "  InstallerSha256: DEF",
            ]);

        WingetManifestHelper.RemoveElevationProhibited(versionDir);

        var lines = File.ReadAllLines(installerPath);
        CollectionAssert.DoesNotContain(lines, "  ElevationRequirement: elevationProhibited");
        CollectionAssert.Contains(lines, "  Scope: user");
        CollectionAssert.Contains(lines, "  InstallerSha256: ABC");
        CollectionAssert.Contains(lines, "  InstallerSha256: DEF");

        Directory.Delete(root, recursive: true);
    }

    [TestMethod]
    public void RemoveElevationProhibited_leavesMachineOnlyInstallerYamlUnchanged()
    {
        var root = Path.Combine(Path.GetTempPath(), "winget-test-" + Guid.NewGuid().ToString("N"));
        var versionDir = Path.Combine(root, "manifests", "p", "pyRevit", "pyRevit", "6.5.0.26173");
        Directory.CreateDirectory(versionDir);

        var installerPath = Path.Combine(versionDir, "pyRevit.pyRevit.installer.yaml");
        var original =
            string.Join(
                Environment.NewLine,
                "Installers:",
                "- Architecture: x64",
                "  Scope: machine",
                "  InstallerSha256: DEF",
                "");
        File.WriteAllText(installerPath, original);

        WingetManifestHelper.RemoveElevationProhibited(versionDir);

        Assert.AreEqual(original, File.ReadAllText(installerPath));

        Directory.Delete(root, recursive: true);
    }

    [TestMethod]
    public void FindVersionManifestDirectory_locatesPackageVersionFolder()
    {
        var root = Path.Combine(Path.GetTempPath(), "winget-test-" + Guid.NewGuid().ToString("N"));
        var versionDir = Path.Combine(root, "manifests", "p", "pyRevit", "pyRevit.CLI", "6.5.0.26173");
        Directory.CreateDirectory(versionDir);
        File.WriteAllText(Path.Combine(versionDir, "pyRevit.pyRevit.CLI.installer.yaml"), "PackageVersion: 6.5.0.26173");

        var found = WingetManifestHelper.FindVersionManifestDirectory(root, "pyRevit.pyRevit.CLI", "6.5.0.26173");

        Assert.AreEqual(versionDir, found);

        Directory.Delete(root, recursive: true);
    }
}
