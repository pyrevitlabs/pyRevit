using System.Reflection;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using Build.Helpers;
using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
[TestCategory("HostFree")]
[TestCategory("Unit")]
public sealed class ChocoPackagesTests
{
    private static readonly XNamespace NuspecNamespace = "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd";

    [TestMethod]
    public void Packages_are_the_cli_and_the_full_product()
    {
        CollectionAssert.AreEquivalent(
            new[] { "pyrevit-cli", "pyrevit" },
            PyRevitPaths.ChocoPackages.Select(package => package.Id).ToList());
    }

    [TestMethod]
    public void Nuspec_id_matches_the_package_id()
    {
        foreach (var package in PyRevitPaths.ChocoPackages)
        {
            var id = XDocument.Load(package.Nuspec).Descendants(NuspecNamespace + "id").Single().Value;
            Assert.AreEqual(package.Id, id, package.Nuspec);
        }
    }

    [TestMethod]
    public void Install_script_has_the_lines_the_pack_step_rewrites()
    {
        foreach (var package in PyRevitPaths.ChocoPackages)
        {
            var lines = File.ReadAllLines(package.InstallScript);
            Assert.AreEqual(1, lines.Count(line => line.StartsWith("$url64", StringComparison.Ordinal)), package.Id);
            Assert.AreEqual(1, lines.Count(line => line.TrimStart().StartsWith("checksum64 ", StringComparison.Ordinal)), package.Id);
        }
    }

    [TestMethod]
    public void Install_script_downloads_the_admin_installer_of_its_own_product()
    {
        var expectedInstallerPrefix = new Dictionary<string, string>
        {
            ["pyrevit-cli"] = "pyRevit_CLI_",
            ["pyrevit"] = "pyRevit_",
        };

        foreach (var package in PyRevitPaths.ChocoPackages)
        {
            var url = File.ReadAllLines(package.InstallScript)
                .Single(line => line.StartsWith("$url64", StringComparison.Ordinal));
            StringAssert.Contains(url, "_admin_signed.exe", package.Id);
            StringAssert.Contains(url, "/" + expectedInstallerPrefix[package.Id], package.Id);
            Assert.AreEqual(package.Id == "pyrevit-cli", url.Contains("/pyRevit_CLI_", StringComparison.Ordinal), package.Id);
        }
    }

    [TestMethod]
    public void Uninstall_script_matches_only_the_inno_uninstall_name_of_its_own_product()
    {
        var displayNames = new Dictionary<string, string>
        {
            ["pyrevit-cli"] = "pyRevit CLI version 7.1.0.26316",
            ["pyrevit"] = "pyRevit version 7.1.0.26316",
        };

        foreach (var package in PyRevitPaths.ChocoPackages)
        {
            var uninstallScript = Path.Combine(
                Path.GetDirectoryName(package.InstallScript)!,
                "chocolateyuninstall.ps1");
            var softwareName = Regex.Match(
                File.ReadAllText(uninstallScript),
                @"softwareName\s*=\s*'([^']*)'").Groups[1].Value;
            var pattern = "^" + Regex.Escape(softwareName).Replace("\\*", ".*") + "$";

            foreach (var (id, displayName) in displayNames)
            {
                Assert.AreEqual(
                    id == package.Id,
                    Regex.IsMatch(displayName, pattern, RegexOptions.IgnoreCase),
                    $"{package.Id} vs {displayName}");
            }
        }
    }

    [TestMethod]
    public void Nupkg_name_follows_choco_pack_naming()
    {
        var package = PyRevitPaths.ChocoPackages.Single(candidate => candidate.Id == "pyrevit");

        Assert.AreEqual("pyrevit.7.1.0.26319.nupkg", package.NupkgName("7.1.0.26319"));
    }

    [TestMethod]
    public void Choco_push_does_not_depend_on_building_or_signing()
    {
        var dependencies = typeof(PublishChocoModule).GetCustomAttributes()
            .Select(attribute => attribute.GetType())
            .Where(type => type.IsGenericType && type.Name.StartsWith("DependsOn", StringComparison.Ordinal))
            .Select(type => type.GenericTypeArguments[0])
            .ToList();

        CollectionAssert.DoesNotContain(dependencies, typeof(SignChocoPackageModule));
        CollectionAssert.DoesNotContain(dependencies, typeof(BuildChocoModule));
    }
}
