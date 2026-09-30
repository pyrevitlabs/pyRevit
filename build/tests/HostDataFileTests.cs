using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

/// <summary>
/// Invariants for release/pyrevit-hosts.json, the registry that decides which Revit a
/// host is and which pyRevit runtime to load for it.
///
/// Nothing else validates this file: it is copied into bin/ by StageBinAssetsModule and
/// deserialized at runtime by JSONDataSource, which falls back to a stale cache on any
/// parse failure. A bad entry therefore shows up as an install that reports the wrong
/// product, or none at all, rather than as a build error. These tests read the committed
/// file so that class of mistake fails CI instead.
/// </summary>
[TestClass]
public sealed class HostDataFileTests
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private static List<HostRecord> LoadHosts()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "pyrevit-hosts.json");
        Assert.IsTrue(File.Exists(path), "Expected fixture copy of release/pyrevit-hosts.json.");
        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<List<HostRecord>>(json, Options)
               ?? throw new InvalidOperationException("pyrevit-hosts.json deserialized to null.");
    }

    [TestMethod]
    public void Committed_file_parses_and_is_not_empty()
    {
        var hosts = LoadHosts();

        Assert.IsGreaterThan(0, hosts.Count);
        Assert.IsTrue(hosts.All(host => !string.IsNullOrWhiteSpace(host.Release)));
        Assert.IsTrue(hosts.All(host => !string.IsNullOrWhiteSpace(host.Version)));
        Assert.IsTrue(hosts.All(host => !string.IsNullOrWhiteSpace(host.Build)));
        Assert.IsTrue(hosts.All(host => !string.IsNullOrWhiteSpace(host.Product)));
        Assert.IsTrue(hosts.All(host => !string.IsNullOrWhiteSpace(host.Target)));
    }

    /// <summary>
    /// A shared release name is not cosmetic. Looking one up matches every record
    /// carrying it, and FindProductInfo then has to fall back on build/version evidence
    /// or refuse to answer, so two builds under one name cannot be told apart. Autodesk
    /// does ship two builds under some release-notes pages, hence the build-date
    /// qualifier, e.g. "2025.4.3 Update" and "2025.4.3 Update (20250815)".
    /// </summary>
    [TestMethod]
    public void Release_names_are_unique_ignoring_case()
    {
        var duplicates = LoadHosts()
            .GroupBy(host => host.Release, StringComparer.OrdinalIgnoreCase)
            .Where(group => group.Count() > 1)
            .Select(group => $"{group.Key} x{group.Count()} (builds: {string.Join(", ", group.Select(h => h.Build))})")
            .ToList();

        Assert.AreEqual(0, duplicates.Count, "Duplicate release name(s): " + string.Join("; ", duplicates));
    }

    /// <summary>
    /// The product year in the name must agree with the version, because the year filter
    /// in FindProductInfo is what narrows a build match to the right record.
    /// </summary>
    [TestMethod]
    public void Release_year_agrees_with_version_year()
    {
        var mismatches = new List<string>();
        foreach (var host in LoadHosts())
        {
            var namedYear = Regex.Match(host.Release, @"\b((19|20)\d{2})\b");
            if (!namedYear.Success)
            {
                continue;
            }

            var versionYear = 2000 + int.Parse(host.Version.Split('.')[0]);
            if (int.Parse(namedYear.Groups[1].Value) != versionYear)
            {
                mismatches.Add($"{host.Release} (version {host.Version})");
            }
        }

        Assert.AreEqual(0, mismatches.Count, "Release/version year mismatch: " + string.Join("; ", mismatches));
    }

    /// <summary>
    /// GetProductYear matches on whitespace followed by four digits
    /// (RevitProduct.cs:223). A name like "Revit 2028" therefore starts resolving the
    /// product year from the name instead of falling through to the version, which
    /// changes what IsSupported and the attachment code paths do. Match any four digits,
    /// not just 19xx or 20xx: the loader would treat a typo'd "Revit 3028" as the product
    /// year, so restricting the pattern here would let that through.
    /// </summary>
    [TestMethod]
    public void Release_names_never_put_whitespace_before_a_four_digit_run()
    {
        var risky = LoadHosts()
            .Select(host => host.Release)
            .Where(name => Regex.IsMatch(name, @"\s+\d{4}"))
            .ToList();

        Assert.AreEqual(0, risky.Count, "Would activate GetProductYear name parsing: " + string.Join("; ", risky));
    }

    [TestMethod]
    public void Versions_are_ordered_numerically_not_lexically()
    {
        var hosts = LoadHosts();
        var outOfOrder = new List<string>();
        for (var i = 1; i < hosts.Count; i++)
        {
            if (CompareVersions(hosts[i].Version, hosts[i - 1].Version) < 0)
            {
                outOfOrder.Add($"{hosts[i - 1].Version} then {hosts[i].Version}");
            }
        }

        Assert.AreEqual(0, outOfOrder.Count, "Out of order: " + string.Join("; ", outOfOrder));
    }

    [TestMethod]
    public void Build_numbers_match_the_expected_shape()
    {
        var malformed = LoadHosts()
            .Where(host => !Regex.IsMatch(host.Build, @"^\d{8}_\d{4}$"))
            .Select(host => $"{host.Release} = {host.Build}")
            .ToList();

        Assert.AreEqual(0, malformed.Count, "Malformed build number(s): " + string.Join("; ", malformed));
    }

    [TestMethod]
    public void Versions_are_parseable_by_dotnet()
    {
        var unparseable = LoadHosts()
            .Where(host => !System.Version.TryParse(host.Version, out _))
            .Select(host => $"{host.Release} = {host.Version}")
            .ToList();

        Assert.AreEqual(0, unparseable.Count, "Unparseable version(s): " + string.Join("; ", unparseable));
    }

    /// <summary>
    /// FindProductInfo drops any record whose meta.schema is not "1.0"
    /// (RevitProduct.cs:164), which makes it invisible rather than invalid. Catch a typo
    /// here instead.
    /// </summary>
    [TestMethod]
    public void Meta_schema_is_the_one_the_loader_accepts()
    {
        var unexpected = LoadHosts()
            .Where(host => !string.Equals(host.Meta?.Schema, "1.0", StringComparison.Ordinal))
            .Select(host => $"{host.Release} = {host.Meta?.Schema ?? "(missing)"}")
            .ToList();

        Assert.AreEqual(0, unexpected.Count, "Unsupported meta.schema: " + string.Join("; ", unexpected));
    }

    /// <summary>
    /// RevitProductData.MinimumSupportedProductYear. A pre-2021 record would be listed as
    /// supported while the C# loader cannot run on it.
    /// </summary>
    [TestMethod]
    public void No_record_sits_below_the_supported_floor()
    {
        const int minimumSupportedProductYear = 2021;
        var tooOld = LoadHosts()
            .Where(host => 2000 + int.Parse(host.Version.Split('.')[0]) < minimumSupportedProductYear)
            .Select(host => $"{host.Release} ({host.Version})")
            .ToList();

        Assert.AreEqual(0, tooOld.Count, "Below the supported floor: " + string.Join("; ", tooOld));
    }

    private static int CompareVersions(string left, string right)
    {
        var leftParts = left.Split('.').Select(int.Parse).ToList();
        var rightParts = right.Split('.').Select(int.Parse).ToList();
        for (var i = 0; i < Math.Max(leftParts.Count, rightParts.Count); i++)
        {
            var l = i < leftParts.Count ? leftParts[i] : 0;
            var r = i < rightParts.Count ? rightParts[i] : 0;
            if (l != r)
            {
                return l.CompareTo(r);
            }
        }

        return 0;
    }

    private sealed class HostRecord
    {
        public string Build { get; set; } = string.Empty;

        public HostMeta? Meta { get; set; }

        public string Notes { get; set; } = string.Empty;

        public string Product { get; set; } = string.Empty;

        public string Release { get; set; } = string.Empty;

        public string Target { get; set; } = string.Empty;

        public string Version { get; set; } = string.Empty;
    }

    private sealed class HostMeta
    {
        [JsonPropertyName("schema")]
        public string? Schema { get; set; }

        public string? Source { get; set; }
    }
}
