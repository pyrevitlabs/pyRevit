namespace Build.Helpers;

public static class WingetManifestHelper
{
    public const string ElevationProhibitedLine = "ElevationRequirement: elevationProhibited";

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
}
