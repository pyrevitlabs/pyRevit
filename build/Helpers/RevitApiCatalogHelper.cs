using System.Text.Json;
using System.Text.RegularExpressions;

namespace Build.Helpers;

/// <summary>
/// Compares the Revit years the committed API catalog covers with the years the C# projects build for, so
/// adding a Revit release without regenerating the catalog fails the build instead of silently narrowing the lint.
/// </summary>
public static partial class RevitApiCatalogHelper
{
    public static IReadOnlyList<int> ReadCatalogYears(string catalogJson)
    {
        using var document = JsonDocument.Parse(catalogJson);
        return document.RootElement.GetProperty("years")
            .EnumerateArray()
            .Select(year => year.GetInt32())
            .Order()
            .ToList();
    }

    /// <summary>
    /// Reads the <c>REVIT&lt;year&gt;</c> constants, ignoring the <c>_OR_GREATER</c> markers.
    /// </summary>
    public static IReadOnlyList<int> ReadBuildTargetYears(string directoryBuildTargets)
    {
        return RevitConstantRegex()
            .Matches(directoryBuildTargets)
            .Select(match => int.Parse(match.Groups[1].Value))
            .Distinct()
            .Order()
            .ToList();
    }

    /// <summary>
    /// Describes how the two year lists differ, or returns <c>null</c> when they match exactly.
    /// </summary>
    public static string? DescribeYearMismatch(IReadOnlyList<int> catalogYears, IReadOnlyList<int> buildTargetYears)
    {
        if (buildTargetYears.Count == 0)
        {
            return "No REVIT<year> constants were found in dev/Directory.Build.targets.";
        }

        var uncovered = buildTargetYears.Except(catalogYears).ToList();
        var stale = catalogYears.Except(buildTargetYears).ToList();
        if (uncovered.Count == 0 && stale.Count == 0)
        {
            return null;
        }

        var parts = new List<string>();
        if (uncovered.Count > 0)
        {
            parts.Add($"built for Revit {string.Join(", ", uncovered)} but missing from the catalog");
        }

        if (stale.Count > 0)
        {
            parts.Add($"cataloged for Revit {string.Join(", ", stale)} but no longer built");
        }

        return "dev/checks/revit_api_catalog/catalog.json is out of date: " + string.Join("; ", parts)
            + ". Regenerate it with dev/checks/build_revit_api_catalog.py.";
    }

    [GeneratedRegex(@";REVIT(\d{4})(?=;|<)")]
    private static partial Regex RevitConstantRegex();
}
