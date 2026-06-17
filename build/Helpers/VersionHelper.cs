using System.Text.RegularExpressions;
using Build.Helpers;
using Build.Models;

namespace Build.Helpers;

public static partial class VersionHelper
{
    [GeneratedRegex(@"\d\.\d+\.\d+(\.[a-z0-9+-]+)?")]
    private static partial Regex VersionFinder();

    [GeneratedRegex(@"^(\d)\.(\d+)\.(\d+)(\.[a-z0-9+-]+)?")]
    private static partial Regex VersionPartFinder();

    public static string ReadBuildVersion(bool urlSafe = false)
    {
        return ReadVersionFromFile(PyRevitPaths.VersionFile, urlSafe);
    }

    public static string ReadInstallVersion(bool urlSafe = false)
    {
        return ReadVersionFromFile(PyRevitPaths.InstallVersionFile, urlSafe);
    }

    public static VersionInfo ReadVersionInfo()
    {
        return CreateVersionInfo(ReadBuildVersion());
    }

    public static string ReadVersionFromFile(string path, bool urlSafe = false)
    {
        var content = File.ReadAllText(path);
        var match = VersionFinder().Match(content);
        if (!match.Success)
        {
            throw new InvalidOperationException($"No version found in {path}");
        }

        var version = match.Value;
        return urlSafe ? version.Replace("+", "%2B", StringComparison.Ordinal) : version;
    }

    public static VersionInfo CreateVersionInfo(string buildVersion)
    {
        var installVersion = buildVersion.Split('+')[0];
        return new VersionInfo(
            buildVersion,
            installVersion,
            buildVersion.Replace("+", "%2B", StringComparison.Ordinal),
            buildVersion.Contains(PyRevitPaths.WipVersionExtension, StringComparison.Ordinal));
    }

    public static string UpdateBuildNumber(string version)
    {
        var match = VersionPartFinder().Match(version);
        if (!match.Success)
        {
            return version;
        }

        var major = match.Groups[1].Value;
        var minor = match.Groups[2].Value;
        var patch = match.Groups[3].Value;
        var build = DateTime.Now.ToString("yy") + DateTime.Now.DayOfYear.ToString("000") + "+" + DateTime.Now.ToString("HHmm");
        return $"{major}.{minor}.{patch}.{build}";
    }

    public static string ApplyChannel(string buildVersion, string channel)
    {
        if (channel.Equals("wip", StringComparison.OrdinalIgnoreCase)
            && !buildVersion.Contains(PyRevitPaths.WipVersionExtension, StringComparison.Ordinal))
        {
            return buildVersion + PyRevitPaths.WipVersionExtension;
        }

        return buildVersion;
    }

    public static void ReplaceVersionInFiles(IEnumerable<string> files, string newVersion)
    {
        foreach (var file in files)
        {
            ReplacePatternInFile(file, VersionFinder(), newVersion);
        }
    }

    public static void ReplacePatternInFile(string filePath, Regex finder, string replacement)
    {
        if (!File.Exists(filePath))
        {
            return;
        }

        var lines = File.ReadAllLines(filePath);
        var changed = false;
        for (var index = 0; index < lines.Length; index++)
        {
            var updated = finder.Replace(lines[index], replacement);
            if (!string.Equals(lines[index], updated, StringComparison.Ordinal))
            {
                lines[index] = updated;
                changed = true;
            }
        }

        if (changed)
        {
            File.WriteAllLines(filePath, lines);
        }
    }

    public static string GetReleaseDownloadBaseUrl(string buildVersionUrlSafe)
    {
        return $"https://github.com/pyrevitlabs/pyRevit/releases/download/v{buildVersionUrlSafe}/";
    }

    public static string GetReleaseTagUrl(string buildVersionUrlSafe)
    {
        return $"https://github.com/pyrevitlabs/pyRevit/releases/tag/v{buildVersionUrlSafe}/";
    }
}
