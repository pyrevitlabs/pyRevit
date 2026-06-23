using System.Text.RegularExpressions;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// Locates the pyRevit config file without depending on the heavier pyRevit
/// libraries, so the lightweight loader and the CLI resolve the same per-user
/// and all-users paths. Roots mirror pyRevitLabs.Common (%APPDATA%\pyRevit and
/// %ProgramData%\pyRevit) and the file-name pattern mirrors pyRevitLabs.PyRevit.
/// </summary>
public static class PyRevitConfigPaths
{
    public const string AppdataDirName = "pyRevit";
    public const string DefaultConfigsFileName = "pyRevit_config.ini";
    public const string ConfigsFileRegexPattern = @".*[pyrevit|config].*\.ini";

    // The all-users installer drops this marker under %ProgramData%\pyRevit.
    public const string InstallAllUsersMarkerFileName = "install_all_users";

    private static bool? _isInstallAllUsers;

    public static string PyRevitAppDataPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), AppdataDirName);

    public static string PyRevitProgramDataPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), AppdataDirName);

    /// <summary>
    /// Writable per-user config target: the first matching file under %APPDATA%,
    /// else the default file name there.
    /// </summary>
    public static string UserConfigFilePath =>
        FindConfigFileInDirectory(PyRevitAppDataPath)
        ?? Path.Combine(PyRevitAppDataPath, DefaultConfigsFileName);

    /// <summary>
    /// All-users config: the first matching file under %ProgramData%, else the
    /// default file name there.
    /// </summary>
    public static string AdminConfigFilePath =>
        FindConfigFileInDirectory(PyRevitProgramDataPath)
        ?? Path.Combine(PyRevitProgramDataPath, DefaultConfigsFileName);

    /// <summary>
    /// True when the all-users installer marker is present. Cached for the process.
    /// </summary>
    public static bool IsInstallAllUsers()
    {
        if (_isInstallAllUsers.HasValue)
            return _isInstallAllUsers.Value;

        string markerPath = Path.Combine(PyRevitProgramDataPath, InstallAllUsersMarkerFileName);
        _isInstallAllUsers = File.Exists(markerPath);
        return _isInstallAllUsers.Value;
    }

    /// <summary>
    /// Returns the first file in <paramref name="directory"/> whose name matches
    /// the config pattern, or null.
    /// </summary>
    public static string? FindConfigFileInDirectory(string directory)
    {
        if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
            return null;

        try
        {
            var matcher = new Regex(ConfigsFileRegexPattern, RegexOptions.IgnoreCase);
            foreach (string file in Directory.GetFiles(directory))
                if (matcher.IsMatch(Path.GetFileName(file)))
                    return file;
        }
        catch
        {
            // Unreadable directory: fall through to the default location.
        }

        return null;
    }
}
