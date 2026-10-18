using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
[TestCategory("HostFree")]
[TestCategory("Unit")]
public sealed class RevitApiCatalogHelperTests
{
    private const string Targets = """
        <PropertyGroup Condition="'$(RevitVersion)' == '2026'">
            <DefineConstants>$(DefineConstants);REVIT2026;REVIT2021_OR_GREATER;REVIT2022_OR_GREATER</DefineConstants>
        </PropertyGroup>
        <PropertyGroup Condition="'$(RevitVersion)' == '2027'">
            <DefineConstants>$(DefineConstants);REVIT2027;REVIT2021_OR_GREATER;REVIT2022_OR_GREATER</DefineConstants>
        </PropertyGroup>
        <PropertyGroup Condition="'$(RevitVersion)' == '2025'">
            <DefineConstants>$(DefineConstants);REVIT2025;REVIT2021_OR_GREATER</DefineConstants>
        </PropertyGroup>
        """;

    [TestMethod]
    public void ReadBuildTargetYears_returns_year_constants_without_or_greater_markers()
    {
        CollectionAssert.AreEqual(new[] { 2025, 2026, 2027 }, RevitApiCatalogHelper.ReadBuildTargetYears(Targets).ToArray());
    }

    [TestMethod]
    public void ReadBuildTargetYears_reads_the_repository_targets_file()
    {
        var years = RevitApiCatalogHelper.ReadBuildTargetYears(File.ReadAllText(PyRevitPaths.DirectoryBuildTargets));

        Assert.IsTrue(years.Contains(2021));
        Assert.IsTrue(years.Count >= 7);
    }

    [TestMethod]
    public void ReadCatalogYears_returns_sorted_years()
    {
        CollectionAssert.AreEqual(
            new[] { 2021, 2022, 2023 },
            RevitApiCatalogHelper.ReadCatalogYears("""{"years": [2023, 2021, 2022], "types": {}}""").ToArray());
    }

    [TestMethod]
    public void DescribeYearMismatch_is_null_when_years_agree()
    {
        Assert.IsNull(RevitApiCatalogHelper.DescribeYearMismatch([2021, 2022], [2021, 2022]));
    }

    [TestMethod]
    public void DescribeYearMismatch_names_a_new_revit_year_missing_from_the_catalog()
    {
        var message = RevitApiCatalogHelper.DescribeYearMismatch([2021, 2022], [2021, 2022, 2028]);

        StringAssert.Contains(message, "Revit 2028 but missing from the catalog");
    }

    [TestMethod]
    public void DescribeYearMismatch_names_a_cataloged_year_that_is_no_longer_built()
    {
        var message = RevitApiCatalogHelper.DescribeYearMismatch([2021, 2022], [2022]);

        StringAssert.Contains(message, "Revit 2021 but no longer built");
    }

    [TestMethod]
    public void DescribeYearMismatch_fails_when_no_build_years_were_found()
    {
        Assert.IsNotNull(RevitApiCatalogHelper.DescribeYearMismatch([2021], []));
    }

    [TestMethod]
    public void Committed_catalog_covers_the_years_the_projects_build_for()
    {
        var catalogYears = RevitApiCatalogHelper.ReadCatalogYears(File.ReadAllText(PyRevitPaths.RevitApiCatalog));
        var buildYears = RevitApiCatalogHelper.ReadBuildTargetYears(File.ReadAllText(PyRevitPaths.DirectoryBuildTargets));

        Assert.IsNull(RevitApiCatalogHelper.DescribeYearMismatch(catalogYears, buildYears));
    }
}
