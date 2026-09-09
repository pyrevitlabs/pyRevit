using System.Text.Json;

namespace Build.Helpers;

/// <summary>
/// The installer set currently published for a package's latest version in microsoft/winget-pkgs.
/// </summary>
public sealed record WingetPublishedInstallers(string LatestVersion, IReadOnlyList<string> InstallerTypes);

public static class WingetManifestHelper
{
    private const string WingetPkgsCatalogApiUrl = "https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests/p/";

    private const string WingetPkgsRawContentUrl = "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/p/";

    public const string ElevationProhibitedLine = "ElevationRequirement: elevationProhibited";

    /// <summary>
    /// Resolves the latest published version of <paramref name="packageId"/> in microsoft/winget-pkgs
    /// and reads its installer types.
    /// Returns null when the package is unpublished or the catalog cannot be reached, letting callers
    /// fail open: wingetcreate independently rejects incompatible updates, so this lookup only exists
    /// to turn those late failures into actionable ones.
    /// </summary>
    public static async Task<WingetPublishedInstallers?> GetPublishedInstallerSetAsync(
        string packageId,
        CancellationToken cancellationToken = default)
    {
        var pathSegments = string.Join('/', packageId.Split('.'));
        using var client = CreateWingetPkgsClient();

        using var listResponse = await client.GetAsync(WingetPkgsCatalogApiUrl + pathSegments, cancellationToken);
        if (!listResponse.IsSuccessStatusCode)
        {
            return null;
        }

        var listedVersions = SelectVersionNames(await listResponse.Content.ReadAsStringAsync(cancellationToken));
        var latestVersion = SelectLatestVersion(listedVersions);
        if (latestVersion is null)
        {
            return null;
        }

        var installerManifestUrl = $"{WingetPkgsRawContentUrl}{pathSegments}/{latestVersion}/{packageId}.installer.yaml";
        using var installerResponse = await client.GetAsync(installerManifestUrl, cancellationToken);
        if (!installerResponse.IsSuccessStatusCode)
        {
            return null;
        }

        var installerYaml = await installerResponse.Content.ReadAsStringAsync(cancellationToken);
        return new WingetPublishedInstallers(latestVersion, ParseInstallerTypes(installerYaml));
    }

    /// <summary>
    /// Extracts the effective InstallerType of each entry in an installer manifest, in order.
    /// Entries inherit the top-level InstallerType unless they declare their own.
    /// </summary>
    public static IReadOnlyList<string> ParseInstallerTypes(string installerYaml)
    {
        var types = new List<string>();
        var topLevelType = string.Empty;
        string? entryType = null;
        var inInstallersSection = false;

        void CloseOpenEntry()
        {
            if (inInstallersSection && entryType is not null)
            {
                types.Add(entryType);
            }

            entryType = null;
        }

        foreach (var rawLine in installerYaml.Replace("\r\n", "\n").Split('\n'))
        {
            if (string.IsNullOrWhiteSpace(rawLine))
            {
                continue;
            }

            var isIndented = rawLine[0] is ' ' or '\t';
            var trimmed = rawLine.Trim();

            if (trimmed.StartsWith("- "))
            {
                CloseOpenEntry();

                if (inInstallersSection)
                {
                    entryType = topLevelType;
                }

                continue;
            }

            if (!isIndented)
            {
                CloseOpenEntry();
                inInstallersSection = trimmed.Equals("Installers:", StringComparison.OrdinalIgnoreCase);

                if (trimmed.StartsWith("InstallerType:", StringComparison.OrdinalIgnoreCase))
                {
                    topLevelType = ExtractYamlScalar(trimmed);
                }

                continue;
            }

            if (inInstallersSection && trimmed.StartsWith("InstallerType:", StringComparison.OrdinalIgnoreCase))
            {
                entryType = ExtractYamlScalar(trimmed);
            }
        }

        CloseOpenEntry();

        return types;
    }

    /// <summary>
    /// Guards against installer-set drift between this pipeline and the published winget catalog:
    /// wingetcreate update only supports replacing installers one-for-one, so any addition or removal
    /// of installers requires a baseline migration PR against microsoft/winget-pkgs first.
    /// Note: equal-count-but-different-types mismatches (e.g. exe swapped for msi) pass this guard and
    /// are rejected later by wingetcreate itself during URL matching.
    /// </summary>
    /// <exception cref="InvalidOperationException">Thrown when the installer counts differ.</exception>
    public static void EnsureCompatibleInstallerCount(
        WingetPublishedInstallers published,
        int intendedInstallerCount,
        string packageId)
    {
        if (published.InstallerTypes.Count == intendedInstallerCount)
        {
            return;
        }

        throw new InvalidOperationException(
            $"WinGet baseline mismatch for {packageId}: the latest published version "
            + $"{published.LatestVersion} in microsoft/winget-pkgs contains {published.InstallerTypes.Count} "
            + $"installer(s) [{string.Join(", ", published.InstallerTypes)}] but this pipeline intends to submit "
            + $"{intendedInstallerCount}. wingetcreate update cannot add or remove installers. "
            + $"Submit a baseline migration PR that publishes the intended installer set for "
            + $"{published.LatestVersion} (or adds a new version with it), merge it, then re-run.");
    }

    public static string FindVersionManifestDirectory(string outputDir, string packageId, string version)
    {
        var expectedFileName = packageId + ".installer.yaml";

        foreach (var file in Directory.EnumerateFiles(outputDir, expectedFileName, SearchOption.AllDirectories))
        {
            var directory = Path.GetDirectoryName(file);
            if (directory is not null
                && string.Equals(Path.GetFileName(directory), version, StringComparison.OrdinalIgnoreCase))
            {
                return directory;
            }
        }

        throw new DirectoryNotFoundException(
            string.Format(
                "Could not find WinGet manifest directory for {0} version {1} under {2}.",
                packageId,
                version,
                outputDir));
    }

    public static void RemoveElevationProhibited(string manifestsRoot)
    {
        foreach (var file in Directory.EnumerateFiles(manifestsRoot, "*.installer.yaml", SearchOption.AllDirectories))
        {
            var lines = File.ReadAllLines(file);
            var filtered = lines.Where(line => !IsElevationProhibitedLine(line)).ToArray();
            if (filtered.Length != lines.Length)
            {
                File.WriteAllLines(file, filtered);
            }
        }
    }

    private static bool IsElevationProhibitedLine(string line) =>
        string.Equals(line.Trim(), ElevationProhibitedLine, StringComparison.OrdinalIgnoreCase);

    private static HttpClient CreateWingetPkgsClient()
    {
        var client = new HttpClient();
        client.DefaultRequestHeaders.UserAgent.ParseAdd("pyrevit-build");
        client.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
        return client;
    }

    private static IReadOnlyList<string> SelectVersionNames(string catalogJson)
    {
        using var document = JsonDocument.Parse(catalogJson);
        var versionNames = new List<string>();

        foreach (var entry in document.RootElement.EnumerateArray())
        {
            if (entry.GetProperty("type").GetString() != "dir")
            {
                continue;
            }

            var name = entry.GetProperty("name").GetString();
            if (name is not null && Version.TryParse(name, out _))
            {
                versionNames.Add(name);
            }
        }

        return versionNames;
    }

    /// <summary>
    /// Returns the highest version among manifest folder names; names that are not versions are ignored.
    /// Returns null when no name is a version.
    /// </summary>
    public static string? SelectLatestVersion(IReadOnlyList<string> versionNames)
    {
        string? latestName = null;
        Version? latestVersion = null;

        foreach (var name in versionNames)
        {
            if (!Version.TryParse(name, out var version))
            {
                continue;
            }

            if (latestVersion is null || version > latestVersion)
            {
                latestVersion = version;
                latestName = name;
            }
        }

        return latestName;
    }

    private static string ExtractYamlScalar(string line)
    {
        return line.Substring(line.IndexOf(':') + 1).Trim().Trim('"', '\'');
    }
}
