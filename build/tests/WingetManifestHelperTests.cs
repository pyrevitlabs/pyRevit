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

    [TestMethod]
    public void ParseInstallerTypes_usesTopLevelTypeForEntriesWithoutOwnType()
    {
        var yaml = string.Join(
            "\n",
            "PackageIdentifier: pyRevit.pyRevit.CLI",
            "InstallerType: inno",
            "Scope: machine",
            "Commands:",
            "- pyrevit",
            "- pyrevit-doctor",
            "Installers:",
            "- Architecture: x64",
            "  InstallerUrl: https://example.com/setup.exe",
            "  InstallerSha256: ABC",
            "ManifestType: installer",
            "");

        var types = WingetManifestHelper.ParseInstallerTypes(yaml);

        CollectionAssert.AreEqual(new[] { "inno" }, types.ToArray());
    }

    [TestMethod]
    public void ParseInstallerTypes_readsExplicitTypesFromEachMultiInstallerEntry()
    {
        var yaml = string.Join(
            "\n",
            "PackageIdentifier: pyRevit.pyRevit.CLI",
            "Scope: machine",
            "Commands:",
            "- pyrevit",
            "Installers:",
            "- Architecture: x64",
            "  InstallerType: inno",
            "  InstallerUrl: https://example.com/setup.exe",
            "  InstallerSha256: ABC",
            "- Architecture: x64",
            "  InstallerType: wix",
            "  InstallerUrl: https://example.com/setup.msi",
            "  InstallerSha256: DEF",
            "ManifestType: installer",
            "");

        var types = WingetManifestHelper.ParseInstallerTypes(yaml);

        CollectionAssert.AreEqual(new[] { "inno", "wix" }, types.ToArray());
    }

    [TestMethod]
    public void SelectLatestVersion_picksHighestVersionAndIgnoresNonVersionFolders()
    {
        var latest = WingetManifestHelper.SelectLatestVersion(["6.5.4.26228", "not-a-version", "6.10.0", "6.9.1"]);

        Assert.AreEqual("6.10.0", latest);
    }

    [TestMethod]
    public void EnsureCompatibleInstallerCount_passesWhenCountsMatch()
    {
        var published = new WingetPublishedInstallers("6.5.5.26237", ["inno", "wix"]);

        WingetManifestHelper.EnsureCompatibleInstallerCount(published, 2, "pyRevit.pyRevit.CLI");
    }

    [TestMethod]
    public void EnsureCompatibleInstallerCount_throwsWithRunbookWhenCountsDiffer()
    {
        var published = new WingetPublishedInstallers("6.5.4.26228", ["inno"]);

        var exception = Assert.ThrowsExactly<InvalidOperationException>(
            () => WingetManifestHelper.EnsureCompatibleInstallerCount(published, 2, "pyRevit.pyRevit.CLI"));

        StringAssert.Contains(exception.Message, "pyRevit.pyRevit.CLI");
        StringAssert.Contains(exception.Message, "6.5.4.26228");
        StringAssert.Contains(exception.Message, "1 installer(s)");
        StringAssert.Contains(exception.Message, "2");
        StringAssert.Contains(exception.Message, "baseline migration PR");
    }
}
